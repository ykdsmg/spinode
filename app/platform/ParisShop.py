import asyncio
from curl_cffi.requests.exceptions import HTTPError
from curl_cffi.requests.session import HttpMethod, AsyncSession
from aiolimiter import AsyncLimiter
from datetime import datetime, timedelta
from app.core.logging import get_logger

logger = get_logger(__name__)


class ParisShop:
    """Paris 店铺。

    - 全局 AsyncSession 由外部（FastAPI lifespan）注入，已内置 RetryStrategy 传输层重试。
    - 统一通过 request() 发送请求，自带 token 刷新 + 可选限流。
    - 调用方无需关心重试，所有连接/超时异常由 session 层面自动处理。
    """

    def __init__(
        self,
        http:           AsyncSession,
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
            resp = await self.http.post(url, headers=headers, verify=False)
            if resp.status_code == 200:
                req = resp.json()
                self.access_token = req["accessToken"]
                self.get_time = datetime.now()
                logger.info("[%s] 刷新 Token 成功", self.seller_id)
            else:
                body = resp.text
                raise RuntimeError(f"刷新 Token 失败: {resp.status_code} {body}")
        except Exception as e:
            logger.error("[%s] 刷新 Token 失败: %s", self.seller_id, e)

    # ═══════════════════════════════════════════════
    #  统一请求入口
    # ═══════════════════════════════════════════════

    # curl_cffi 视为不可重试的状态码（服务端错误，session 传输层已做重试）

    async def request(
        self,
        method: HttpMethod,
        url: str,
        *,
        limiter: AsyncLimiter | None = None,
        timeout: int = 30,
        headers: dict | None = None,
        params: dict | None = None,
        **kwargs,
    ) -> dict:
        """统一 HTTP 请求入口。

        传输层重试由 curl_cffi AsyncSession 内置的 RetryStrategy 承担（连接超时/DNS/SSL 等）。
        本方法不再叠加应用层重试，仅做 token 刷新、限流控制与服务端错误记录。

        工作流:
            valid_token() → 合并 headers → AsyncLimiter（如有）→ HTTP 请求 → JSON 解析

        Args:
            method:   HTTP 方法 (GET/POST/…)。
            url:      请求路径（自动拼接 base_url）。
            limiter:  可选 AsyncLimiter，有 QPM 需求的 Resource 传入。
            timeout:  单个 HTTP 请求超时（秒，默认 30）。
            headers:  额外请求头，与 shop 基础 headers 合并。
            params:   URL 查询参数字典。
            **kwargs: 透传给 curl_cffi session.request()（如 json / data 等）。

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

        # ── 4. 发送请求（带可选限流） ──────────────
        async def _send():
            return await self.http.request(
                method      = method,
                url         = full_url,
                timeout     = timeout,
                headers     = merged_headers,
                params      = params,
                verify      = False,
                **kwargs,
            )

        try:
            if limiter:
                async with limiter:
                    resp = await _send()
            else:
                resp = await _send()
            resp.raise_for_status()
            return resp.json()
        except HTTPError as e:
                # HTTP 状态码错误 (4xx/5xx)
                status = e.response.status_code if e.response else "N/A"
                logger.error(
                    "[%s] HTTP错误 %s %s -> %s",
                    self.seller_id, method, full_url, status
                )
                raise
        except Exception as e:
            # 网络错误、JSON解析错误等
            logger.error(
                "[%s] 请求异常 %s %s: %s",
                self.seller_id, method, full_url, e
            )
            raise
