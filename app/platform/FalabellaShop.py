import hashlib
import hmac
import urllib.parse
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.http.client import HttpClient

logger = get_logger(__name__)


class FalabellaShop:
    def __init__(
        self,
        seller_id: str | None = None,
        user_id: str | None = None,
        api_key: str | None = None,
        business_unit: str | None = None,
        shop_name: str | None = None,
        shop_names: str | None = None,
        integration_type: str  = "PROPIA",
        timezone: str | None = None,
    ):
        # ── 店铺基础信息 ──────────────────────────────
        self.seller_id = seller_id
        self.user_id = user_id
        self.api_key = api_key
        self.business_unit = business_unit
        self.shop_name = shop_name
        self.shop_names = shop_names
        self.integration_type = integration_type or "PROPIA"
        self.timezone = timezone
        self.base_url = "https://sellercenter-api.falabella.com/"

    # ────────────────────────────────────────────────
    #  签名方法
    # ────────────────────────────────────────────────
    def _generate_signature(self, parameters: dict[str, str]) -> str:
        """HMAC-SHA256 签名: 参数排序 → key=value& 拼接 → HMAC 摘要。"""
        concatenated = urllib.parse.urlencode(sorted(parameters.items()))
        return hmac.new(
            key=self.api_key.encode("utf-8"),
            msg=concatenated.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

    # ────────────────────────────────────────────────
    #  请求参数
    # ────────────────────────────────────────────────
    def _build_params(self, action: str, params: dict | None = None) -> dict:
        """构建公共参数 (不含签名)。"""
        date = {
            "Action": action,
            "Format": "JSON",
            "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            "UserID": self.user_id,
            "Version": "1.0",
        }
        if params:
            for k, v in params.items():
                if v is not None:
                    date[k] = str(v) if not isinstance(v, str) else v
        return date

    # ────────────────────────────────────────────────
    #  请求头
    # ────────────────────────────────────────────────
    def _build_headers(self) -> dict[str, str]:
        return {
            "User-Agent": f"{self.seller_id}/Python/3.11/{self.integration_type}/{self.business_unit}"
        }

    # ────────────────────────────────────────────────
    #  url
    # ────────────────────────────────────────────────
    def _build_url(self, action: str, params: dict = {}, Format: str = "JSON") -> str:
        """构建请求 URL。"""
        params.update(
            {
                "Action": action,
                "Format": Format,
                "Timestamp": datetime.now(timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%S+00:00"
                ),
                "UserID": self.user_id,
                "Version": "1.0",
            }
        )
        params["Signature"] = self._generate_signature(params)
        query_string = urllib.parse.urlencode(params, doseq=True)
        return f"{self.base_url}?{query_string}"

    def fetch(self, client: HttpClient, method: str, action: str, params: dict = {}):
        params = {k: v for k, v in params.items() if v is not None}
        url = self._build_url(action, params)
        headers = self._build_headers()
        try:
            resp = client.request_sync(method=method, url=url, headers=headers)
            return resp.json()
        except Exception as e:
            print(e)
            return {}
