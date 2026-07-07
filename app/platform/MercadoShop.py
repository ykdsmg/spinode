import asyncio
from datetime import datetime, timedelta

import requests

from app.core.logging import get_logger
from app.db.manager import DBManager
from app.http.client import HttpClient

logger = get_logger(__name__)

# Token 到期前提前刷新的分钟数
_REFRESH_LEAD_MINUTES = 30


class MercadoShop:
    def __init__(
        self,
        app_id: str,
        secret: str,
        user_id: str,
        seller_id: str,
        shop_name: str,
        shop_names: str,
        business_unit: str,
        timezone: str,
        access_token: str,
        refresh_token: str,
        get_time: str,
        expires_in: int = 21600,
    ) -> None:
        # ── 店铺基础信息 ──────────────────────────────
        self.app_id = app_id
        self.secret = secret
        self.user_id = user_id
        self.seller_id = seller_id
        self.shop_name = shop_name
        self.shop_names = shop_names
        self.business_unit = business_unit
        self.timezone = timezone
        self.base_url = "https://api.mercadolibre.com"
        self.token_url = "https://api.mercadolibre.com/oauth/token"

        # ── Token 信息 ────────────────────────────────
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_in = expires_in
        self.get_time = datetime.fromisoformat(get_time)

        # ── 并发安全 (每个店铺独立锁) ─────────────────
        self._token_lock = asyncio.Lock()
        self._client = HttpClient(async_mode=False)

    # ────────────────────────────────────────────────
    #  Token 过期判断 & 刷新
    # ────────────────────────────────────────────────

    @property
    def _expires_at(self) -> datetime:
        """Token 过期时间。"""
        return self.get_time + timedelta(seconds=self.expires_in)

    @property
    def _should_refresh(self) -> bool:
        """是否需要刷新 (提前 30 分钟)。"""
        return datetime.now() >= self._expires_at - timedelta(
            minutes=_REFRESH_LEAD_MINUTES
        )

    @property
    async def valid_token(self):
        """保证 access_token 有效。若过期则自动刷新 (线程安全)。"""
        if not self._should_refresh:
            return
        async with self._token_lock:
            # double-check: 防止多个协程同时刷新 Token
            if not self._should_refresh:
                return
            await self._refresh_token

    @property
    async def _refresh_token(self):
        """执行 OAuth Token 刷新, 并更新 DB。"""

        headers = {
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "refresh_token",
            "client_id": self.app_id,
            "client_secret": self.secret,
            "refresh_token": self.refresh_token,
        }
        req = None
        try:
            response = self._client.request_sync(
                method="POST", url=self.token_url, headers=headers, data=data
            )

            refresh_token = self.refresh_token

            req = response.json()
            self.access_token = req["access_token"]
            self.refresh_token = req["refresh_token"]
            self.expires_in = req["expires_in"]
            self.get_time = datetime.now()
            logger.info(f"{self.seller_id} 刷新 Token 成功")

            if req:
                req["GetTime"] = self.get_time
                req["state"] = 1
                await DBManager.execute(
                    "UPDATE mercado_token SET state = 0 WHERE user_id = %s AND refresh_token = %s",
                    (self.user_id, refresh_token),
                )
                await DBManager.upsert(
                    "mercado_token", req, ["user_id", "refresh_token"]
                )
        except requests.exceptions.RequestException as e:
            logger.error(f"刷新 Token 失败: {e}")

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}

    async def fetch(
        self, client: HttpClient, method: str, url: str, headers: dict | None = None
    ):
        try:
            url = f"{self.base_url}{url}"
            headers = self._headers().update(headers) if headers else self._headers()
            self.valid_token
            resp = await client.request_async(method=method, url=url, headers=headers)
            return await resp.json()
        except Exception as e:
            print(e)
            return {}
