"""HTTP 重试公共组件。

每个 Shop 内部自行组装 http_request，共用这里的重试条件和异常。
"""

import asyncio

from curl_cffi.requests.exceptions import (
    ConnectionError,
    RequestException,
    Timeout,
)
from tenacity import (
    retry as tenacity_retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# ── 重试判断条件 ─────────────────────────────────────

# 触发重试的状态码
RETRY_STATUS = {408, 429, 500, 502, 503, 504}

# 触发重试的异常类型
RETRY_EXCEPTIONS = (
    RequestException,
    ConnectionError,
    Timeout,
    asyncio.TimeoutError,
)


class RetryableStatusError(Exception):
    """遇到可重试状态码时抛出，触发 tenacity 重试。"""

    def __init__(self, status: int, body: str = ""):
        self.status = status
        self.body = body
        super().__init__(f"HTTP {status}: {body[:200]}")


def build_retry_decorator(max_retries: int = 5, backoff_factor: float = 1.0):
    """构建 tenacity 重试装饰器，复用重试条件和退避策略。"""
    return tenacity_retry(
        retry=retry_if_exception_type(RETRY_EXCEPTIONS + (RetryableStatusError,)),
        wait=wait_exponential(
            multiplier=backoff_factor,
            min=1,
            max=60,
        ),
        stop=stop_after_attempt(max_retries),
        reraise=True,
    )
