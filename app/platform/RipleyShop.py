"""ripley 店铺（异步版）。

- 全局 aiohttp ClientSession 由外部（FastAPI lifespan）注入。
- 统一通过 request() 发送请求，tenacity 重试：网络错误 + 指定状态码重试。
- 限流器（AsyncLimiter）对每次重试尝试都计数。
"""
from aiolimiter     import AsyncLimiter
from aiohttp        import ClientSession, ClientResponseError, ClientTimeout
from tenacity       import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)

from app.core.logging       import get_logger

logger = get_logger(__name__)

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


class RipleyShop:
    """Ripley 店铺。

    - OAuth2 认证，refresh_token 过期后自动续期并写 DB。
    - tenacity 重试：网络错误 + 指定状态码 {429,500,502,503,504} 重试（最多 5 次），每次尝试计入限流。
    """

    def __init__(
        self,
        http:           ClientSession,
        api_key:        str | None = None,
        shop_id:        str | None = None,
        shop_name:      str | None = None,
        shop_code:      str | None = None,
        country:        str | None = None,
        time_zone:       str | None = None,
    ) -> None:
        self.api_key        = api_key
        self.shop_id        = shop_id
        self.shop_name      = shop_name
        self.shop_code      = shop_code
        self.country        = country
        self.time_zone       = time_zone
        self.base_url       = "https://ripley-prod.mirakl.net"

        self.http           = http

    # ═══════════════════════════════════════════════
    #  Headers
    # ═══════════════════════════════════════════════

    def _build_headers(self) -> dict:
        return {
            "Authorization": self.api_key,
        }

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
            合并 headers → 重试循环 → AsyncLimiter（每次尝试）→ HTTP → JSON

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
        # ── 1. 合并 headers ─────────────────────────
        merged_headers = self._build_headers()
        if headers:
            merged_headers.update(headers)

        # ── 2. 拼接完整 URL ─────────────────────────
        if other_url:
            full_url = f"{other_url}{url}"
        else:
            full_url = f"{self.base_url}{url}"

        # ── 3. 发送请求（重试 + 限流：每次尝试独立计次）──
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
                self.shop_id, method, full_url, status
            )
            raise
        except Exception as e:
            logger.error(
                "[%s] 请求异常 %s %s: %s",
                self.shop_id, method, full_url, e
            )
            raise
