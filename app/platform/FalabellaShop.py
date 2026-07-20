"""Falabella 店铺（同步版）。

- 同步请求，全局 Session 由外部（FastAPI lifespan）注入。
- 每次请求 HMAC-SHA256 签名，无需 token。
- tenacity 重试：网络错误 + 指定状态码自动重试（最多 5 次，指数退避）。
"""
import requests
import hashlib
import hmac
import urllib.parse
from datetime import datetime, timezone
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════
#  重试配置（tenacity）
# ═══════════════════════════════════════════════

# 可重试的 HTTP 状态码
_RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})

def _should_retry(exc: BaseException) -> bool:
    """网络错误始终重试；HTTP 错误仅在白名单状态码重试。"""
    if isinstance(exc, requests.exceptions.HTTPError):
        if exc.response is not None:
            return exc.response.status_code in _RETRYABLE_STATUSES
    return True

_retry = retry(
    retry   = retry_if_exception(_should_retry),
    wait    = wait_exponential(multiplier=1, min=1, max=60),
    stop    = stop_after_attempt(5),
    reraise = True,
)


class FalabellaShop:
    """Falabella 店铺。

    - 签名算法: HMAC-SHA256 (Action + 公共参数排序 → 签名)。
    - tenacity 重试：网络错误 + 指定状态码 {429,500,502,503,504} 重试（最多 5 次）。
    """

    def __init__(
        self,
        seller_id:          str,
        user_id:            str,
        api_key:            str,
        business_unit:      str,
        shop_name:          str,
        shop_names:         str,
        http:               requests.Session,
        timezone:           str,
        integration_type:   str = "PROPIA",
    ):
        self.seller_id          = seller_id
        self.user_id            = user_id
        self.api_key            = api_key
        self.business_unit      = business_unit
        self.shop_name          = shop_name
        self.shop_names         = shop_names
        self.http               = http
        self.integration_type   = integration_type or "PROPIA"
        self.timezone           = timezone
        self.base_url           = "https://sellercenter-api.falabella.com/"

    # ═══════════════════════════════════════════════
    #  签名
    # ═══════════════════════════════════════════════

    def _generate_signature(self, params: dict[str, str]) -> str:
        """HMAC-SHA256 签名。参数按 key 排序 → key=value& 拼接 → HMAC 摘要。"""
        concatenated = urllib.parse.urlencode(sorted(params.items()))
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

    def _build_params(self, action: str, params: dict | None = None):
        """构建带签名的完整请求 URL。

        Args:
            action: API 动作名（如 GetProducts / GetOrders）。
            params: 业务参数，会自动合并公共参数并签名。
        """
        merged = {
            "Action":       action,
            "Format":       "JSON",
            "Timestamp":    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            "UserID":       self.user_id,
            "Version":      "1.0",
        }
        if params:
            merged.update(params)
        merged["Signature"] = self._generate_signature(merged)

        return merged

    # ═══════════════════════════════════════════════
    #  统一请求入口
    # ═══════════════════════════════════════════════

    def request(
        self,
        method: str,
        action: str,
        *,
        timeout: int = 60,
        params: dict | None = None,
    ) -> dict:
        """统一 HTTP 请求入口，自带签名。

        tenacity 重试：网络错误 + 指定状态码 {429,500,502,503,504}
        自动重试（最多 5 次，指数退避），其余错误直接抛出。

        工作流:
            _build_params(action, params) → _build_headers() → HTTP 请求 → JSON 解析

        Args:
            method:     HTTP 方法 (GET/POST/…)。
            action:     API 动作名（GetProducts / GetOrders …）。
            timeout:    单个 HTTP 请求超时（秒，默认 60）。
            params:     业务参数字典，会自动合并公共参数并签名。

        Returns:
            dict — JSON 响应体，失败时返回空 dict。
        """
        # ── 1. 构建 URL + Headers ──────────────────
        req_params = self._build_params(action, params)
        headers    = self._build_headers()

        # ── 2. 发送请求（带重试） ────────────────────
        @_retry
        def _call() -> dict:
            resp = self.http.request(
                method      = method,
                url         = self.base_url,
                timeout     = timeout,
                headers     = headers,
                params      = req_params,
            )
            resp.raise_for_status()
            return resp.json()

        try:
            return _call()
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "N/A"
            logger.error(
                "[%s] HTTP错误 %s %s -> %s",
                self.seller_id, method, action, status
            )
            raise
        except Exception as e:
            logger.error(
                "[%s] 请求异常 %s %s: %s",
                self.seller_id, method, action, e
            )
            raise
