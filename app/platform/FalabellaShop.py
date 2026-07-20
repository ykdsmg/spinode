"""Falabella 店铺（同步版）。

- 同步请求，全局 Session 由外部（FastAPI lifespan）注入。
- 每次请求 HMAC-SHA256 签名，无需 token。
- 应用层 backon 重试：网络错误 + 指定状态码自动重试（最多 5 次，指数退避）。
"""
import requests
import hashlib
import hmac
import urllib.parse
import backon
from datetime import datetime, timezone
from app.core.logging import get_logger

logger = get_logger(__name__)


class FalabellaShop:
    """Falabella 店铺。

    - 签名算法: HMAC-SHA256 (Action + 公共参数排序 → 签名)。
    - 应用层 backon 重试：网络错误 + 指定状态码自动重试（最多 5 次，指数退避）。
    """

    # 可重试的 HTTP 状态码
    _RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})

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

        应用层 backon 重试：网络错误 + 指定状态码 {429,500,502,503,504}
        自动重试（最多 5 次，指数退避），其余错误直接抛出。

        工作流:
            _build_params(action, params) → _build_headers() → backon.retry(HTTP 请求) → JSON 解析

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

        # ── 2. 重试条件：网络错误 + 指定状态码 ──────────
        retryable = self._RETRYABLE_STATUSES

        def _giveup(exc: Exception) -> bool:
            """非网络错误且非指定状态码 → 放弃重试。"""
            if isinstance(exc, requests.exceptions.HTTPError):
                if exc.response is not None:
                    return exc.response.status_code not in retryable
            return False  # 网络错误 → 继续重试

        # ── 3. 实际 HTTP 调用 ─────────────────────────
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

        # ── 4. 执行（带重试） ─────────────────────────
        try:
            return backon.retry(
                _call,
                backon.expo,
                exception   = Exception,
                max_tries   = 5,
                giveup      = _giveup,
            )
        except requests.exceptions.HTTPError as e:
            # HTTP 状态码错误 — 不可重试的已被 giveup 拦截
            status = e.response.status_code if e.response else "N/A"
            logger.error(
                "[%s] HTTP错误 %s %s -> %s",
                self.seller_id, method, action, status
            )
            raise
        except Exception as e:
            # 网络错误等 — 重试耗尽后仍失败
            logger.error(
                "[%s] 请求异常 %s %s: %s",
                self.seller_id, method, action, e
            )
            raise
