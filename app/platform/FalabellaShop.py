"""Falabella 店铺（同步版）。

- 同步请求，全局 Session 由外部（FastAPI lifespan）注入，无重试。
- 每次请求 HMAC-SHA256 签名，无需 token。
"""
import requests
import hashlib
import hmac
import urllib.parse
from datetime import datetime, timezone
from app.core.logging import get_logger

logger = get_logger(__name__)


class FalabellaShop:
    """Falabella 店铺。

    - 签名算法: HMAC-SHA256 (Action + 公共参数排序 → 签名)。
    """

    def __init__(
        self,
        seller_id: str,
        user_id: str,
        api_key: str,
        business_unit: str,
        shop_name: str,
        shop_names: str,
        http: requests.Session,
        integration_type: str = "PROPIA",
        timezone: str | None = None,
    ):
        self.seller_id = seller_id
        self.user_id = user_id
        self.api_key = api_key
        self.business_unit = business_unit
        self.shop_name = shop_name
        self.shop_names = shop_names
        self.http = http
        self.integration_type = integration_type or "PROPIA"
        self.timezone = timezone
        self.base_url = "https://sellercenter-api.falabella.com/"

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

        工作流:
            _build_url(action, params) → _build_headers() → HTTP 请求 → JSON 解析

        Args:
            method:     HTTP 方法 (GET/POST/…)。
            action:     API 动作名（GetProducts / GetOrders …）。
            timeout:    单个 HTTP 请求超时（秒，默认 30）。
            params:     业务参数字典，会自动合并公共参数并签名。

        Returns:
            dict — JSON 响应体，失败时返回空 dict。
        """
        # ── 1. 构建 URL + Headers ──────────────────
        params = self._build_params(action, params)

        headers = self._build_headers()

        # ── 2. 发送请求 ────────────────────────────
        try:
            resp = self.http.request(
                method      = method,
                url         = self.base_url,
                timeout     = timeout,
                headers     = headers,
                params      = params,
                # verify      = False,
            )
            if resp:
                resp.raise_for_status()
            else:
                raise ValueError("响应为空")
        except Exception as e:
            logger.error(
                "[%s] 请求失败 %s: %s",
                self.seller_id, action, e,
            )
            return {}

        try:
            return resp.json()
        except Exception as e:
            logger.error(
                "[%s] JSON 解析失败 %s: %s",
                self.seller_id, action, e,
            )
            return {}
