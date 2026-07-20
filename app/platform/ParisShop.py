import backon
import asyncio
from aiohttp        import ClientSession, ClientResponseError, ClientTimeout
from aiolimiter     import AsyncLimiter
from datetime       import datetime, timedelta

from app.core.logging import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════
#  重试配置（backon）
# ═══════════════════════════════════════════════

# 可重试的 HTTP 状态码
_RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})

def _giveup(exc: Exception) -> bool:
    """非网络错误且非指定状态码 → 放弃重试。"""
    if isinstance(exc, ClientResponseError):
        return exc.status not in _RETRYABLE_STATUSES
    return False  # 网络错误 → 继续重试

_retry = backon.on_exception(
    backon.expo,
    exception   = Exception,
    max_tries   = 5,
    giveup      = _giveup,
)


class ParisShop:
    """Paris 店铺。

    - 全局 aiohttp ClientSession 由外部（FastAPI lifespan）注入。
    - 统一通过 request() 发送请求，自带 token 刷新 + 可选限流。
    - 应用层 backon 重试：网络错误 + 指定状态码 {429,500,502,503,504} 重试（最多 5 次）。
    """

    def __init__(
        self,
        http:           ClientSession,
        seller_id:      str,
        user_id:        str | None = None,
        api_key:        str | None = None,
        country:        str | None = None,
        shop_name:      str | None = None,
        shop_code:      str | None = None,
        time_zone:      str | None = None,
    ):
        self.seller_id      = seller_id
        self.user_id        = user_id
        self.api_key        = api_key
        self.country        = country
        self.shop_name      = shop_name
        self.shop_code      = shop_code
        self.time_zone      = time_zone
        self.access_token   = None
        self.expires_in     = 14400
        self.get_time       = None
        self.base_url       = "https://api-developers.ecomm.cencosud.com"

        self.http           = http

        self._token_lock    = asyncio.Lock()

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

    async def valid_token(self):
        """保证 access_token 有效，过期则自动刷新（线程安全）。"""
        if not self._should_refresh():
            return
        async with self._token_lock:
            if not self._should_refresh():
                return
            await self._refresh_token()

    async def _refresh_token(self):
        """使用全局 session 异步刷新 Token。"""
        url = f"{self.base_url}/v1/auth/apiKey"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        try:
            async with self.http.post(url, headers=headers, ssl=False) as resp:
                if resp.status == 200:
                    req = await resp.json()
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

    # 非指定状态码不可重试，网络错误 + 指定状态码由 backon 自动重试

    async def request(
        self,
        method: str,
        url: str,
        *,
        limiter: AsyncLimiter | None = None,
        timeout: int = 30,
        headers: dict | None = None,
        params: dict | None = None,
        **kwargs,
    ) -> dict:
        """统一 HTTP 请求入口。

        应用层 backon 重试：网络错误 + 指定状态码 {429,500,502,503,504}
        自动重试（最多 5 次，指数退避），其余错误直接抛出。

        工作流:
            valid_token() → 合并 headers → AsyncLimiter（如有）→ HTTP 请求 → JSON 解析

        Args:
            method:   HTTP 方法 (GET/POST/…)。
            url:      请求路径（自动拼接 base_url）。
            limiter:  可选 AsyncLimiter，有 QPM 需求的 Resource 传入。
            timeout:  单个 HTTP 请求超时（秒，默认 30）。
            headers:  额外请求头，与 shop 基础 headers 合并。
            params:   URL 查询参数字典。
            **kwargs: 透传给 aiohttp session.request()（如 json / data 等）。

        Returns:
            dict — JSON 响应体，失败时返回空 dict。
        """
        # ── 1. 刷新 token ──────────────────────────
        await self.valid_token()

        # ── 2. 构建 headers ─────────────────────────
        merged_headers = {"Accept": "application/json"}
        token = self.access_token
        if token:
            merged_headers["Authorization"] = f"Bearer {token}"
        if headers:
            merged_headers.update(headers)

        # ── 3. 拼接完整 URL ─────────────────────────
        full_url = f"{self.base_url}{url}"

        # ── 4. 发送请求（带 backon 重试 + 可选限流） ──
        @_retry
        async def _send():
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

        try:
            if limiter:
                async with limiter:
                    return await _send()
            else:
                return await _send()
        except ClientResponseError as e:
            # HTTP 状态码错误 (4xx/5xx) — 5xx 已被 backon 重试过
            status = e.status
            logger.error(
                "[%s] HTTP错误 %s %s -> %s",
                self.seller_id, method, full_url, status
            )
            raise
        except Exception as e:
            # 网络错误、JSON解析错误等 — 已被 backon 重试过
            logger.error(
                "[%s] 请求异常 %s %s: %s",
                self.seller_id, method, full_url, e
            )
            raise
