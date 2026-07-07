import asyncio
from datetime import datetime, timedelta

from app.core.logging import get_logger
from app.http.client import HttpClient

logger = get_logger(__name__)


class ParisShop:
    def __init__(
        self,
        seller_id: str,
        user_id: str,
        api_key: str,
        country: str,
        shop_name: str,
        shop_code: str,
        time_zone: str,
    ):
        # ── 店铺基础信息 ──────────────────────────────
        self.seller_id = seller_id
        self.user_id = user_id
        self.api_key = api_key
        self.country = country
        self.shop_name = shop_name
        self.shop_code = shop_code
        self.time_zone = time_zone
        self.access_token = None
        self.expires_in = 14400
        self.get_time = None
        self.base_url = "https://api-developers.ecomm.cencosud.com"

        self._token_lock = asyncio.Lock()
        self._client = HttpClient(async_mode=False)

    def _expires_at(self) -> datetime:
        """Token 过期时间。"""
        if self.get_time:
            return datetime.now() + timedelta(seconds=self.expires_in)
        else:
            return datetime(1970, 1, 1)

    def _should_refresh(self) -> bool:
        """是否需要刷新 (提前 10 分钟)。"""
        return datetime.now() >= self._expires_at() - timedelta(minutes=10)

    async def valid_token(self):
        """保证 access_token 有效。若过期则自动刷新 (线程安全)。"""
        if not self._should_refresh():
            return
        async with self._token_lock:
            if not self._should_refresh():
                return
            self._refresh_token()

    def _refresh_token(self):
        """执行 Token 刷新"""
        req = None
        url = "https://api-developers.ecomm.cencosud.com/v1/auth/apiKey"
        try:
            resp = self._client.request_sync(
                method="POST", url=url, headers=self._headers()
            )
            if resp.status_code == 200:
                req = resp.json()
                self.access_token = req["accessToken"]
                self.get_time = datetime.now()
                logger.info(f"{self.seller_id} 刷新 Token 成功")
            else:
                raise Exception(f"刷新 Token 失败: {resp.status_code} {resp.text}")
        except Exception as e:
            logger.error(f"刷新 Token 失败: {e}")

    def _headers(self) -> dict:
        if self.access_token:
            return {
                "Accept": "application/json",
                "Authorization": f"Bearer {self.access_token}",
            }
        else:
            return {
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }

    async def fetch(
        self,
        client: HttpClient,
        method: str,
        url: str,
        headers: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        try:
            url = f"{self.base_url}{url}"
            await self.valid_token()
            self_headers = self._headers()
            if self_headers:
                headers = self_headers.update(headers) if headers else self_headers
                async with client as client:
                    resp = await client.request_async(
                        method=method, url=url, headers=headers, params=params
                    )
                return await resp.json()
            else:
                logger.error(f"请求失败: url = {url}, headers = {headers}, params = {params}")
                return {}
        except Exception as e:
            logger.error(f"请求失败: url = {url}, headers = {headers}, params = {params}, error = {e}")
            return {}
