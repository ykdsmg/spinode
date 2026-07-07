"""Mercado 账单资源: BillingPeriods / PeriodsBilling(ML/MP/FLEX/FULL) / Summary / GenerationReport / Download。

BillingPeriods: 拉取可用的账单期间列表 → upsert billing_periods 表
PeriodsBilling: 按期间 key + group 拉取账单明细 (分页) → 按 group 插入对应表
"""

from __future__ import annotations

import asyncio
import json

from app.db import repository
from app.http.client import HttpClient
from app.platform.base import Resource, Shop
from app.platforms.mercado.config import MercadoClient
from app.platforms.mercado.converters import BILLING_PARSER


_BILLING_TABLE = {
    "ML": "mercado_billing_ml",
    "MP": "mercado_billing_mp",
    "FLEX": "mercado_billing_flex",
    "FULL": "mercado_billing_full",
}


class BillingResource(Resource):
    """账单资源。"""

    def __init__(self, shop: "Shop") -> None:
        super().__init__(shop)

    async def _headers(self) -> dict:
        await self.shop.credential.ensure_valid()
        token = self.shop.credential.data.get("access_token", "")
        return {"Authorization": f"Bearer {token}"}

    # ── BillingPeriods ─────────────────────────────────

    async def billing_periods(
        self, group: str, document_type: str = "BILL", offset: int = 0, limit: int = 100
    ) -> dict:
        headers = await self._headers()
        url = (f"{self.shop.platform.settings.base_url}/billing/integration/monthly/periods"
               f"?group={group}&document_type={document_type}&offset={offset}&limit={limit}")
        async with HttpClient(timeout=30) as client:
            resp = await client.request("GET", url, headers=headers)
        if resp.status != 200:
            return {}
        return await resp.json()

    def parse_periods(self, raw: dict, group_id: str) -> list[dict]:
        results = raw.get("results", []) or []
        seller_id = int(self.shop.shop_id)
        return [{
            "seller_id": seller_id,
            "group_id": group_id,
            "amount": r.get("amount"),
            "unpaid_amount": r.get("unpaid_amount"),
            "date_from": r.get("date_from"),
            "date_to": r.get("date_to"),
            "period_key": r.get("key"),
            "expiration_date": r.get("expiration_date"),
            "debt_expiration_date": r.get("debt_expiration_date"),
            "debt_expiration_date_move_reason": r.get("debt_expiration_date_move_reason"),
            "debt_expiration_date_move_reason_description": r.get("debt_expiration_date_move_reason_description"),
            "period_status": r.get("period_status"),
        } for r in results if isinstance(r, dict)]

    async def store_periods(self, items: list[dict]) -> int:
        if not items:
            return 0
        await repository.upsert_batch("billing_periods", items, ["seller_id", "period_key", "group_id"])
        return len(items)

    async def sync_periods(self, group: str = "ML", document_type: str = "BILL") -> int:
        """拉取并存储账单期间列表。"""
        raw = await self.billing_periods(group, document_type, offset=0, limit=100)
        items = self.parse_periods(raw, group)
        if items:
            await self.store_periods(items)
        self.logger.info("[%s] Billing Periods (%s) 同步: %s 条", self.shop.shop_id, group, len(items))
        return len(items)

    # ── PeriodsBilling ─────────────────────────────────

    async def periods_billing(
        self, key: str, group: str, document_type: str = "BILL", limit: int = 1000, from_id: int = 0
    ) -> dict:
        headers = await self._headers()
        base_url = self.shop.platform.settings.base_url
        if group == "ML":
            url = f"{base_url}/billing/integration/periods/key/{key}/group/ML/details?document_type={document_type}&limit={limit}&from_id={from_id}&sort_by=DATE&order_by=ASC"
        elif group == "MP":
            url = f"{base_url}/billing/integration/periods/key/{key}/group/MP/details?document_type={document_type}&limit={limit}&from_id={from_id}&sort_by=DATE&order_by=ASC"
        elif group == "FLEX":
            url = f"{base_url}/billing/integration/periods/key/{key}/group/ML/flex/details?document_type={document_type}&limit={limit}&from_id={from_id}&sort_by=DATE&order_by=ASC"
        elif group == "FULL":
            url = f"{base_url}/billing/integration/periods/key/{key}/group/ML/full/details?document_type={document_type}&limit={limit}&from_id={from_id}&sort_by=DATE&order_by=ASC"
        else:
            raise ValueError(f"未知 billing group: {group}")
        async with HttpClient(timeout=60) as client:
            resp = await client.request("GET", url, headers=headers)
        if resp.status != 200:
            return {}
        return await resp.json()

    async def sync_periods_billing(self, key: str, group: str, document_type: str = "BILL", limit: int = 1000) -> int:
        """拉取某个期间的账单明细 (自动翻页)。"""
        parser = BILLING_PARSER.get(group.upper())
        if not parser:
            self.logger.error("未知账单 group: %s", group)
            return 0
        table = _BILLING_TABLE.get(group.upper(), f"mercado_billing_{group.lower()}")

        from_id = 0
        total = 0
        first = True
        all_count = 0

        while True:
            raw = await self.periods_billing(key, group, document_type, limit, from_id)
            if first:
                first = False
                total = raw.get("total", 0)
                self.logger.info("[%s] PeriodsBilling %s/%s: total=%s", self.shop.shop_id, group, key, total)

            results = raw.get("results", []) or []
            if not results:
                break
            seller_id = int(self.shop.shop_id)
            items = parser(results)
            for item in items:
                item["seller_id"] = seller_id
                item["key_id"] = key
            if items:
                await repository.insert_batch(table, items)
                all_count += len(items)
                self.logger.info("[%s] billing %s: +%s (累计 %s/%s)", self.shop.shop_id, group, len(items), all_count, total)

            from_id = raw.get("last_id")
            if not from_id or len(results) < limit:
                break

        self.logger.info("[%s] PeriodsBilling %s/%s 完成: %s 条", self.shop.shop_id, group, key, all_count)
        return all_count

    # ── GenerationReport ────────────────────────────────

    async def generation_report(self, key: str, group: str, document_type: str, report_format: str = "CSV") -> dict:
        headers = await self._headers()
        headers["Content-Type"] = "application/json"
        body = {"group": group, "document_type": document_type, "report_format": report_format}
        url = f"{self.shop.platform.settings.base_url}/billing/integration/periods/key/{key}/reports"
        async with HttpClient(timeout=30) as client:
            resp = await client.request("POST", url, headers=headers, json=body)
        if resp.status != 200:
            return {}
        return await resp.json()

    async def generation_report_status(self, file_id: str) -> dict:
        headers = await self._headers()
        url = f"{self.shop.platform.settings.base_url}/billing/integration/reports/{file_id}/status?document_type=BILL"
        async with HttpClient(timeout=30) as client:
            resp = await client.request("GET", url, headers=headers)
        if resp.status != 200:
            return {}
        return await resp.json()

    async def download_report(self, file_id: str) -> bytes | None:
        headers = await self._headers()
        url = f"{self.shop.platform.settings.base_url}/billing/integration/reports/{file_id}?document_type=BILL"
        async with HttpClient(timeout=120) as client:
            resp = await client.request("GET", url, headers=headers)
        if resp.status != 200:
            return None
        return await resp.content()

    async def sync_download_report(
        self, key: str, group: str, document_type: str = "BILL", report_format: str = "CSV"
    ) -> str | None:
        """生成报告 → 轮询状态 → 下载到本地文件。"""
        gen = await self.generation_report(key, group, document_type, report_format)
        file_id = gen.get("file_id")
        if not file_id:
            self.logger.warning("生成报告失败: %s", gen)
            return None

        for _ in range(10):
            status_resp = await self.generation_report_status(file_id)
            status = status_resp.get("status") if isinstance(status_resp, dict) else None
            if status == "READY":
                break
            await asyncio.sleep(10)
        else:
            self.logger.warning("报告 %s 超时未就绪", file_id)
            return None

        content = await self.download_report(file_id)
        if content:
            file_path = f"resource/mercado/{file_id}"
            import os
            os.makedirs("resource/mercado", exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(content)
            self.logger.info("报告已下载: %s", file_path)
            return file_path
        return None

    async def billing_summary_details(self, key: str) -> dict | None:
        headers = await self._headers()
        url = f"{self.shop.platform.settings.base_url}/billing/integration/periods/key/{key}/summary/details?document_type=BILL"
        async with HttpClient(timeout=30) as client:
            resp = await client.request("GET", url, headers=headers)
        if resp.status != 200:
            return None
        return await resp.json()
