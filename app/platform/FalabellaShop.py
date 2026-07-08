"""Falabella 店铺（同步版）。

- 同步请求，直接使用 requests，无需外部注入 session。
- 每次请求 HMAC-SHA256 签名，无需 token。
- 统一通过 request() 发送请求，自带重试逻辑。
"""

import hashlib
import hmac
import urllib.parse
from datetime import datetime, timezone

import requests
from tenacity import (
    retry as tenacity_retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.logging import get_logger

logger = get_logger(__name__)

# 触发重试的请求异常
RETRY_EXCEPTIONS = (
    requests.exceptions.Timeout,
    requests.exceptions.ConnectionError,
    requests.exceptions.HTTPError,
)
# 触发重试的状态码
RETRY_STATUS = {408, 429, 500, 502, 503, 504}


class RetryableSyncError(Exception):
    """遇到可重试状态码时抛出，触发 tenacity 重试。"""

    def __init__(self, status: int, body: str = ""):
        self.status = status
        self.body = body
        super().__init__(f"HTTP {status}: {body[:200]}")


class FalabellaShop:
    """Falabella 店铺。

    - 签名算法: HMAC-SHA256 (Action + 公共参数排序 → 签名)。
    - 同步请求，session 由外部（FastAPI lifespan）注入。
    """

    def __init__(
        self,
        seller_id: str,
        user_id: str,
        api_key: str,
        business_unit: str,
        shop_name: str,
        shop_names: str,
        integration_type: str = "PROPIA",
        timezone: str | None = None,
    ):
        self.seller_id = seller_id
        self.user_id = user_id
        self.api_key = api_key
        self.business_unit = business_unit
        self.shop_name = shop_name
        self.shop_names = shop_names
        self.integration_type = integration_type or "PROPIA"
        self.timezone = timezone
        self.base_url = "https://sellercenter-api.falabella.com/"

    # ═══════════════════════════════════════════════
    #  签名
    # ═══════════════════════════════════════════════

    def _generate_signature(self, parameters: dict[str, str]) -> str:
        """HMAC-SHA256 签名。参数按 key 排序 → key=value& 拼接 → HMAC 摘要。"""
        concatenated = urllib.parse.urlencode(sorted(parameters.items()))
        return hmac.new(
            key=self.api_key.encode("utf-8"),
            msg=concatenated.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

    # ═══════════════════════════════════════════════
    #  URL & Headers
    # ═══════════════════════════════════════════════

    def _build_headers(self) -> dict[str, str]:
        return {
            "User-Agent": f"{self.seller_id}/Python/3.11/{self.integration_type}/{self.business_unit}"
        }

    def _build_url(self, action: str, params: dict | None = None) -> str:
        """构建带签名的完整请求 URL。

        Args:
            action: API 动作名（如 GetProducts / GetOrders）。
            params: 业务参数，会自动合并公共参数并签名。
        """
        merged = {
            "Action": action,
            "Format": "JSON",
            "Timestamp": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S+00:00"
            ),
            "UserID": self.user_id,
            "Version": "1.0",
        }
        if params:
            merged.update({k: str(v) if not isinstance(v, str) else v
                           for k, v in params.items() if v is not None})
        merged["Signature"] = self._generate_signature(merged)
        query_string = urllib.parse.urlencode(merged, doseq=True)
        return f"{self.base_url}?{query_string}"

    # ═══════════════════════════════════════════════
    #  统一请求入口
    # ═══════════════════════════════════════════════

    def request(
        self,
        method: str,
        action: str,
        *,
        max_retries: int = 5,
        backoff_factor: float = 1.0,
        timeout: int = 30,
        params: dict | None = None,
    ) -> dict:
        """统一 HTTP 请求入口，自带签名 + 重试。

        工作流:
            _build_url(action, params) → _build_headers() → tenacity 重试循环
                └── 遇到 408/429/50x 或网络异常自动重试（指数退避）

        Args:
            action:         API 动作名（GetProducts / GetOrders …）。
            max_retries:    最大重试次数（默认 5）。
            backoff_factor: 指数退避乘数（默认 1.0）。
            timeout:        单个 HTTP 请求超时（秒，默认 30）。
            params:         业务参数字典，会自动合并公共参数并签名。

        Returns:
            dict — JSON 响应体，失败时返回空 dict。
        """
        # ── 1. 构建 URL + Headers ──────────────────
        url = self._build_url(action, params)
        headers = self._build_headers()

        # ── 2. 重试 ────────────────────────────────
        retry_decorator = tenacity_retry(
            retry=retry_if_exception_type(
                RETRY_EXCEPTIONS + (RetryableSyncError,)
            ),
            wait=wait_exponential(
                multiplier=backoff_factor,
                min=1,
                max=30,
            ),
            stop=stop_after_attempt(max_retries),
            reraise=True,
        )

        @retry_decorator
        def _attempt() -> requests.Response:
            resp = requests.request(
                method,
                url,
                headers=headers,
                timeout=timeout,
            )
            if resp.status_code in RETRY_STATUS:
                raise RetryableSyncError(resp.status_code, resp.text[:500])
            return resp

        # ── 3. 执行并返回 JSON ─────────────────────
        try:
            resp = _attempt()
            return resp.json()
        except Exception as e:
            logger.error(
                "[%s] 请求失败 %s: %s",
                self.seller_id, action, e,
            )
            return {}
