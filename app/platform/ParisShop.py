import asyncio
from datetime import datetime, timedelta
import json

import aiohttp
from aiolimiter import AsyncLimiter

from app.http.retry import (
    RETRY_STATUS,
    RetryableStatusError,
    build_retry_decorator,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class ParisShop:
    """Paris 店铺。

    - 全局 session 由外部传入，本类不持有任何 session。
    - 统一通过 request() 发送请求，自带 token 刷新 + 重试 + 可选限流。
    """

    def __init__(
        self,
        seller_id: str | None = None,
        user_id: str | None = None,
        api_key: str | None = None,
        country: str | None = None,
        shop_name: str | None = None,
        shop_code: str | None = None,
        time_zone: str | None = None,
    ):
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

    # ═══════════════════════════════════════════════
    #  Token 管理
    # ═══════════════════════════════════════════════

    def _expires_at(self) -> datetime:
        if self.get_time:
            return self.get_time + timedelta(seconds=self.expires_in)
        return datetime(1970, 1, 1)

    def _should_refresh(self) -> bool:
        """是否需要刷新（提前 10 分钟）。"""
        return datetime.now() >= self._expires_at() - timedelta(minutes=10)

    async def valid_token(self, session: aiohttp.ClientSession):
        """保证 access_token 有效，过期则自动刷新（线程安全）。"""
        if not self._should_refresh():
            return
        async with self._token_lock:
            if not self._should_refresh():
                return
            await self._refresh_token(session)

    async def _refresh_token(self, session: aiohttp.ClientSession):
        """使用全局 session 异步刷新 Token。"""
        url = f"{self.base_url}/v1/auth/apiKey"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        try:
            async with session.post(url, headers=headers, ssl=False) as resp:
                if resp.status == 200:
                    req = await resp.json()
                    with open(f"data/{self.api_key}.json", "w", encoding="utf-8") as f:
                        json.dump(req, f, ensure_ascii=False, indent=4)
                    self.access_token = req["accessToken"]
                    self.get_time = datetime.now()
                    logger.info("[%s] 刷新 Token 成功", self.seller_id)
                else:
                    body = await resp.text()
                    raise RuntimeError(f"刷新 Token 失败: {resp.status} {body}")
        except Exception as e:
            logger.error("[%s] 刷新 Token 失败: %s", self.seller_id, e)

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
        timeout: int = 30,
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

        # ── 2. 构建 headers ─────────────────────────
        merged_headers = {"Accept": "application/json"}
        token = self.access_token
        if token:
            merged_headers["Authorization"] = f"Bearer {token}"
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
                    **kwargs,
                )

            # 每次 HTTP 尝试都独立走限流（防止重试绕过 QPM 限制）
            if limiter:
                async with limiter:
                    resp = await _send()
            else:
                resp = await _send()

            # 遇到可重试状态码 → 抛出异常触发 tenacity 重试
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
