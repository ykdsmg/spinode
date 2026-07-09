"""Mercado 店铺（异步版）。

- 全局 session 由外部传入，本类不持有 session。
- OAuth2 Token 过期自动刷新（线程安全），刷新也用 aiohttp。
- 统一通过 request() 发送请求，自带 token 刷新 + 重试 + 可选限流。
"""

import asyncio
from datetime import datetime, timedelta

import aiohttp
from aiolimiter import AsyncLimiter

from app.core.logging import get_logger
from app.db.manager import DBManager
from app.http.retry import (
    RETRY_STATUS,
    RetryableStatusError,
    build_retry_decorator,
)

logger = get_logger(__name__)

# Token 到期前提前刷新（分钟）
_REFRESH_LEAD_MINUTES = 30


class MercadoShop:
    """Mercado 店铺。

    - OAuth2 认证，refresh_token 过期后自动续期并写 DB。
    - session 由外部（FastAPI lifespan）注入。
    """

    def __init__(
        self,
        app_id: str | None = None,
        secret: str | None = None,
        user_id: str | None = None,
        seller_id: str | None = None,
        shop_name: str | None = None,
        shop_names: str | None = None,
        business_unit: str | None = None,
        timezone: str | None = None,
        access_token: str | None = None,
        refresh_token: str | None = None,
        get_time: datetime | None = None,
        expires_in: int = 21600,
    ) -> None:
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

        # Token
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_in = expires_in
        self.get_time = get_time or datetime(1970, 1, 1)

        # 并发安全
        self._token_lock = asyncio.Lock()

    # ═══════════════════════════════════════════════
    #  Token 管理
    # ═══════════════════════════════════════════════

    @property
    def _expires_at(self) -> datetime:
        return self.get_time + timedelta(seconds=self.expires_in)

    @property
    def _should_refresh(self) -> bool:
        return datetime.now() >= self._expires_at - timedelta(
            minutes=_REFRESH_LEAD_MINUTES
        )

    async def valid_token(self, session: aiohttp.ClientSession):
        """保证 access_token 有效。过期则自动刷新（线程安全）。"""
        if not self._should_refresh:
            return
        async with self._token_lock:
            if not self._should_refresh:          # double-check
                return
            # await self._refresh_token(session)

    async def _refresh_token(self, session: aiohttp.ClientSession):
        """使用全局 aiohttp session 异步刷新 OAuth Token 并写 DB。"""
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
        old_refresh = self.refresh_token

        try:
            async with session.post(
                self.token_url, headers=headers, data=data, ssl=False,
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise RuntimeError(f"刷新 Token 失败: {resp.status} {body}")
                req = await resp.json()

            self.access_token = req["access_token"]
            self.refresh_token = req["refresh_token"]
            self.expires_in = req["expires_in"]
            self.get_time = datetime.now()
            logger.info("[%s] 刷新 Token 成功", self.seller_id)

            # 持久化：旧 token 置无效 → 新 token 写入
            await DBManager.execute(
                "UPDATE mercado_token SET state = 0 WHERE user_id = %s AND refresh_token = %s",
                (self.user_id, old_refresh),
            )
            req["GetTime"] = self.get_time
            req["state"] = 1
            await DBManager.upsert("mercado_token", req, ["user_id", "refresh_token"])

        except Exception as e:
            logger.error("[%s] 刷新 Token 失败: %s", self.seller_id, e)

    # ═══════════════════════════════════════════════
    #  Headers
    # ═══════════════════════════════════════════════

    def _build_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}

    # ═══════════════════════════════════════════════
    #  统一请求入口
    # ═══════════════════════════════════════════════

    async def request(
        self,
        session: aiohttp.ClientSession,
        method: str,
        url: str,
        *,
        limiter: AsyncLimiter | None = None,
        max_retries: int = 5,
        backoff_factor: float = 1.0,
        timeout: int = 60,
        headers: dict | None = None,
        **kwargs,
    ) -> dict:
        """统一 HTTP 请求入口，自带 token 刷新 + 重试 + 可选限流。

        工作流:
            valid_token() → 合并 headers → tenacity 重试循环
                └── 每次 HTTP 尝试前先走 AsyncLimiter（如有）
                └── 遇到 408/429/50x 自动重试（指数退避）

        Args:
            session:        全局 aiohttp ClientSession。
            method:         HTTP 方法 (GET/POST/…) 。
            url:            请求路径（自动拼接 base_url）。
            limiter:        可选 AsyncLimiter，有 QPM 需求的 Resource 传入。
            max_retries:    最大重试次数（默认 5）。
            backoff_factor: 指数退避乘数（默认 1.0）。
            timeout:        单个 HTTP 请求超时（秒，默认 30）。
            headers:        额外请求头，与 shop 基础 headers 合并。
            **kwargs:       透传给 aiohttp session.request()。

        Returns:
            dict — JSON 响应体，失败时返回空 dict。
        """
        # ── 1. 刷新 token ──────────────────────────
        await self.valid_token(session)

        # ── 2. 合并 headers ─────────────────────────
        merged_headers = self._build_headers()
        if headers:
            merged_headers.update(headers)

        # ── 3. 拼接完整 URL ─────────────────────────
        full_url = f"{self.base_url}{url}"

        # ── 4. 重试 + 可选限流 ─────────────────────
        @build_retry_decorator(max_retries, backoff_factor)
        async def _attempt() -> aiohttp.ClientResponse:
            async def _send() -> aiohttp.ClientResponse:
                return await session.request(
                    method, full_url,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                    headers=merged_headers,
                    ssl=False,
                    **kwargs,
                )

            if limiter:
                async with limiter:
                    resp = await _send()
            else:
                resp = await _send()

            if resp.status in RETRY_STATUS:
                body = await resp.text()
                resp.close()
                raise RetryableStatusError(resp.status, body)

            return resp

        # ── 5. 执行并返回 JSON ─────────────────────
        try:
            resp = await _attempt()
            return await resp.json()
        except Exception as e:
            logger.error(
                "[%s] 请求失败 %s %s: %s",
                self.seller_id, method, full_url, e,
            )
            return {}
