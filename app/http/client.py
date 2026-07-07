"""统一 HTTP 客户端。

- 每个接口在发请求时 新建 一个 HttpClient 实例, 从而可单独配置: timeout / max_retries / backoff_factor / limiter (AsyncLimiter 控制单个接口速率)。
- 同时支持 异步 (aiohttp, 默认) 与 同步 (requests)。
- 响应统一封装为 ApiResponse, 屏蔽两种底层库差异。
- 重试: 异步用 tenacity (指数退避), 同步用 urllib3 Retry。

典型用法 (异步):
    async with HttpClient(timeout=50, limiter=AsyncLimiter(90)) as client:
        resp = await client.request("GET", url, headers=headers)
        data = await resp.json()

典型用法 (同步):
    with HttpClient(async_mode=False) as client:
        resp = client.request_sync("GET", url, headers=headers)
"""

import asyncio

import aiohttp
import requests
from aiolimiter import AsyncLimiter
from requests.adapters import HTTPAdapter
from tenacity import (
    retry as tenacity_retry,
)
from tenacity import (
    retry_if_exception_type,
    retry_if_result,
    stop_after_attempt,
    wait_exponential,
)
from urllib3.util.retry import Retry

from app.core.logging import get_logger

logger = get_logger(__name__)

# 触发重试的状态码
_RETRY_STATUS = {408, 429, 500, 502, 503, 504}


class HttpClient:
    """每个接口内部实例化的 HTTP 客户端, 支持异步 (默认) 与同步。

    Args:
        timeout:          请求总超时 (秒)。
        max_retries:      最大重试次数。
        backoff_factor:   指数退避乘数。
        limiter:          可选 AsyncLimiter, 用于控制该接口请求速率。
        async_mode:       True=异步(aiohttp), False=同步(requests)。
        pool_size:        连接池大小。
    """

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 5,
        backoff_factor: float = 1.0,
        qpm: int | None = None,
        async_mode: bool = True,
        pool_size: int = 20,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.async_mode = async_mode
        self.pool_size = pool_size
        # 限流（仅异步生效）
        self.limiter: AsyncLimiter | None = (
            AsyncLimiter(qpm) if qpm is not None else None
        )
        self._req_session: requests.Session | None = None
        self._aio_session: aiohttp.ClientSession | None = None
        self._aio_timeout: aiohttp.ClientTimeout | None = aiohttp.ClientTimeout(
            total=timeout
        )

    async def __aenter__(self):
            # 延迟创建 session，避免未使用时浪费资源
            if self._aio_session is None:
                self._aio_session = self._create_aio_session()
            return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._aio_session is not None:
            await self._aio_session.close()
            self._aio_session = None

    # ===================== session 构建 =====================

    def _create_aio_session(self) -> aiohttp.ClientSession:
        connector = aiohttp.TCPConnector(
            limit=self.pool_size,
            limit_per_host=self.pool_size,
            keepalive_timeout=60,
            ssl=False,
        )
        return aiohttp.ClientSession(connector=connector, timeout=self._aio_timeout)

    def _create_req_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=self.max_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=_RETRY_STATUS,
            allowed_methods=["GET", "POST"],
            raise_on_status=False,
            read=self.max_retries,
            connect=self.max_retries,
        )
        adapter = HTTPAdapter(
            max_retries=retry,
            pool_connections=self.pool_size,
            pool_maxsize=self.pool_size,
            pool_block=False,
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    # ===================== 异步请求 =====================

    def _should_retry_status(self, status: int) -> bool:
        return status in _RETRY_STATUS

    def _build_retry_decorator(self):

        return tenacity_retry(
            retry=(
                retry_if_exception_type(
                    (
                        aiohttp.ClientError,
                        asyncio.TimeoutError,
                        aiohttp.ClientConnectionError,
                        aiohttp.ServerTimeoutError,
                    )
                )
                | retry_if_result(self._should_retry_status)
            ),
            wait=wait_exponential(
                multiplier=self.backoff_factor,
                min=1,
                max=30,
            ),
            stop=stop_after_attempt(self.max_retries),
            reraise=True,
        )

    async def request_async(
        self, method: str, url: str, headers=None, params=None, json=None, data=None
    ):
        """发送异步请求,"""
        if self._aio_session is None:
            self._aio_session = self._create_aio_session()

        method_upper = method.upper()

        @self._build_retry_decorator()
        async def _do():
            async def _send() -> aiohttp.ClientResponse:
                return await self._aio_session.request(
                    method_upper,
                    url,
                    headers=headers,
                    params=params,
                    json=json,
                    data=data,
                    ssl=False,
                )

            if self.limiter is not None:
                async with self.limiter:
                    resp = await _send()
            else:
                resp = await _send()
            return resp

        try:
            return await _do()
        except Exception as e:
            logger.error("异步请求失败 %s %s: %s", method_upper, url, e)
            raise

    # ===================== 同步请求 =====================

    def request_sync(
        self, method: str, url: str, headers=None, params=None, json=None, data=None
    ):
        """发送同步请求 (requests)"""
        if self._req_session is None:
            self._req_session = self._create_req_session()

        method_upper = method.upper()
        resp = self._req_session.request(
            method_upper,
            url,
            headers=headers,
            params=params,
            json=json,
            data=data,
            timeout=self.timeout,
        )
        return resp
