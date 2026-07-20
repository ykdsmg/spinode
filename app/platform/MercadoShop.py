"""Mercado 店铺（异步版）。

- 全局 aiohttp ClientSession 由外部（FastAPI lifespan）注入。
- OAuth2 Token 过期自动刷新（线程安全）。
- 统一通过 request() 发送请求，tenacity 重试：网络错误 + 指定状态码重试。
- 限流器（AsyncLimiter）对每次重试尝试都计数。
"""
import asyncio
from aiolimiter     import AsyncLimiter
from aiohttp        import ClientSession, ClientResponseError, ClientTimeout
from datetime       import datetime, timedelta
from tenacity       import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)

from app.core.logging       import get_logger
from app.db.manager         import DBManager

logger = get_logger(__name__)

# Token 到期前提前刷新（分钟）
_REFRESH_LEAD_MINUTES = 30


# ═══════════════════════════════════════════════
#  重试配置（tenacity）
# ═══════════════════════════════════════════════

# 可重试的 HTTP 状态码
_RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})

def _should_retry(exc: BaseException) -> bool:
    """网络错误始终重试；HTTP 错误仅在白名单状态码重试。"""
    if isinstance(exc, ClientResponseError):
        return exc.status in _RETRYABLE_STATUSES
    return True

_retry = retry(
    retry   = retry_if_exception(_should_retry),
    wait    = wait_exponential(multiplier=1, min=1, max=60),
    stop    = stop_after_attempt(5),
    reraise = True,
)


class MercadoShop:
    """Mercado 店铺。

    - OAuth2 认证，refresh_token 过期后自动续期并写 DB。
    - tenacity 重试：网络错误 + 指定状态码 {429,500,502,503,504} 重试（最多 5 次），每次尝试计入限流。
    """

    def __init__(
        self,
        http:           ClientSession,
        app_id:         str | None = None,
        secret:         str | None = None,
        user_id:        str | None = None,
        seller_id:      str | None = None,
        shop_name:      str | None = None,
        shop_names:     str | None = None,
        business_unit:  str | None = None,
        timezone:       str | None = None,
        access_token:   str | None = None,
        refresh_token:  str | None = None,
        get_time:       datetime | None = None,
        expires_in:     int = 21600,
    ) -> None:
        self.app_id         = app_id
        self.secret         = secret
        self.user_id        = user_id
        self.seller_id      = seller_id
        self.shop_name      = shop_name
        self.shop_names     = shop_names
        self.business_unit  = business_unit
        self.timezone       = timezone
        self.base_url       = "https://api.mercadolibre.com"
        self.token_url      = "https://api.mercadolibre.com/oauth/token"
        # Token
        self.access_token   = access_token
        self.refresh_token  = refresh_token
        self.expires_in     = expires_in
        self.get_time       = get_time or datetime(1970, 1, 1)

        self.http           = http
        # 并发安全
        self._token_lock    = asyncio.Lock()

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

    async def valid_token(self):
        """保证 access_token 有效。过期则自动刷新（线程安全）。"""
        if not self._should_refresh:
            return
        async with self._token_lock:
            if not self._should_refresh:          # double-check
                return
            await self._refresh_token()

    async def _refresh_token(self):
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
        resp = None

        try:
            # ── 1. 发送 HTTP 请求 ──────────────────────────
            async with self.http.post(
                self.token_url, headers=headers, data=data
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise RuntimeError(f"刷新 Token 失败: {resp.status} {body}")

                # ── 2. 解析 JSON 响应 ──────────────────────────
                req = await resp.json()

            self.access_token    = req["access_token"]
            self.refresh_token   = req["refresh_token"]
            self.expires_in      = req["expires_in"]
            self.get_time        = datetime.now()
            logger.info("[%s] 刷新 Token 成功", self.seller_id)

            # ── 3. 持久化到 DB ────────────────────────────
            req["GetTime"] = self.get_time
            req["state"] = 1
            await DBManager.upsert("mercado_token", req, ["user_id", "refresh_token"])

            await DBManager.execute(
                "UPDATE mercado_token SET state = 0 WHERE user_id = %s AND refresh_token = %s",
                (self.seller_id, old_refresh),
            )

        except Exception as e:
            if resp is not None:
                try:
                    resp_body = await resp.text()
                except Exception:
                    resp_body = "<无法读取响应体>"
                logger.error(
                    "[%s] 刷新 Token 失败: %s | HTTP状态码: %s | 响应体: %s",
                    self.seller_id, e, resp.status, resp_body,
                )
            else:
                logger.error(
                    "[%s] 刷新 Token 请求异常 (未获得响应): %s",
                    self.seller_id, e,
                )

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
        method: str,
        url: str,
        *,
        limiter: AsyncLimiter | None = None,
        timeout: int = 50,
        other_url: str | None = None,
        headers: dict | None = None,
        params:  dict | None = None,
        **kwargs,
    ) -> dict:
        """统一 HTTP 请求入口。

        tenacity 重试：网络错误 + 指定状态码 {429,500,502,503,504}
        自动重试（最多 5 次，指数退避），每次尝试计入 AsyncLimiter。

        工作流:
            valid_token() → 合并 headers → 重试循环 → AsyncLimiter（每次尝试）→ HTTP → JSON

        Args:
            method:     HTTP 方法 (GET/POST/…)。
            url:        请求路径（自动拼接 base_url 或 other_url）。
            limiter:    可选 AsyncLimiter，每次重试尝试都会消耗一个令牌。
            timeout:    单个 HTTP 请求超时（秒，默认 50）。
            other_url:  可选替换 base_url（如 MercadoPago）。
            headers:    额外请求头，与 shop 基础 headers 合并。
            params:     URL 查询参数字典。
            **kwargs:   透传给 aiohttp session.request()（如 json / data 等）。

        Returns:
            dict — JSON 响应体，失败时返回空 dict。
        """
        # ── 1. 刷新 token ──────────────────────────
        await self.valid_token()

        # ── 2. 合并 headers ─────────────────────────
        merged_headers = self._build_headers()
        if headers:
            merged_headers.update(headers)

        # ── 3. 拼接完整 URL ─────────────────────────
        if other_url:
            full_url = f"{other_url}{url}"
        else:
            full_url = f"{self.base_url}{url}"

        # ── 4. 发送请求（重试 + 限流：每次尝试独立计次）──
        async def _do_request():
            """单次 HTTP 调用（无重试、无限流）。"""
            t = ClientTimeout(total=timeout)
            async with self.http.request(
                method      = method,
                url         = full_url,
                timeout     = t,
                headers     = merged_headers,
                params      = params,
                **kwargs,
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

        @_retry
        async def _attempt():
            """带重试的单次尝试 — limiter 在每次重试中生效。"""
            if limiter:
                async with limiter:
                    return await _do_request()
            else:
                return await _do_request()

        try:
            return await _attempt()
        except ClientResponseError as e:
            status = e.status
            if status == 404:
                raise

            logger.error(
                "[%s] HTTP错误 %s %s -> %s",
                self.seller_id, method, full_url, status
            )
            raise
        except Exception as e:
            logger.error(
                "[%s] 请求异常 %s %s: %s",
                self.seller_id, method, full_url, e
            )
            raise
