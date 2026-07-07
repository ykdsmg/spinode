"""Mercado 库存资源: Stock/StockF/OperationSearch/Operation/Performance 请求/解析/存储。"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime

from aiolimiter import AsyncLimiter

from app.core.converters import to_int
from app.db import repository
from app.http.client import HttpClient
from app.platform.base import Resource, Shop
from app.platforms.mercado.config import MercadoClient
from app.platforms.mercado.schemas import MercadoProductStock


class StockResource(Resource):
    """库存资源。"""

    def __init__(self, shop: "Shop") -> None:
        super().__init__(shop)
        self._stock_limiter = AsyncLimiter(90, 60)

    async def _headers(self) -> dict:
        await self.shop.credential.ensure_valid()
        token = self.shop.credential.data.get("access_token", "")
        return {"Authorization": f"Bearer {token}"}

    async def stock(self, user_product_id: str) -> dict:
        headers = await self._headers()
        url = f"{self.shop.platform.settings.base_url}/user-products/{user_product_id}/stock"
        async with HttpClient(timeout=30, limiter=self._stock_limiter) as client:
            resp = await client.request("GET", url, headers=headers)
        if resp.status != 200:
            return {}
        return await resp.json()

    async def stock_fulfillment(self, inventory_id: str) -> dict | None:
        headers = await self._headers()
        url = f"{self.shop.platform.settings.base_url}/inventories/{inventory_id}/stock/fulfillment"
        async with HttpClient(timeout=30) as client:
            resp = await client.request("GET", url, headers=headers)
        if resp.status != 200:
            return None
        return await resp.json()

    def parse(self, raw_list: list[dict]) -> list[dict]:
        upsert_date = datetime.now().strftime("%Y-%m-%d")
        result: list[dict] = []
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            locations = item.get("locations", []) or []
            selling_address = meli_facility = seller_warehouse = 0
            for loc in locations:
                t = loc.get("type")
                if t == "selling_address":
                    selling_address = to_int(loc.get("quantity", 0))
                elif t == "meli_facility":
                    meli_facility = to_int(loc.get("quantity", 0))
                elif t == "seller_warehouse":
                    seller_warehouse = to_int(loc.get("quantity", 0))
            result.append({
                "seller_id": int(item.get("user_id", self.shop.shop_id)),
                "upsert_date": upsert_date,
                "user_product_id": item.get("id"),
                "selling_address": selling_address,
                "meli_facility": meli_facility,
                "seller_warehouse": seller_warehouse,
            })
        return result

    async def store(self, items: list[dict]) -> int:
        if not items:
            return 0
        models = [MercadoProductStock(**r) for r in items]
        await repository.upsert_batch("mercado_product_stock", models, ["seller_id", "user_product_id"])
        return len(models)

    async def sync(self) -> int:
        """同步所有商品的库存 (从 mercado_product 表取 user_product_id)。"""
        rows = await repository.select(
            "SELECT DISTINCT user_product_id FROM mercado_product WHERE seller_id = %s AND user_product_id IS NOT NULL",
            [int(self.shop.shop_id)],
        )
        ids = [r["user_product_id"] for r in rows if r["user_product_id"]]
        if not ids:
            return 0

        async def _fetch(upid):
            try:
                return await self.stock(upid)
            except Exception as e:
                self.logger.warning("Stock %s 失败: %s", upid, e)
                return {}

        chunk_size = 50
        all_results: list[dict] = []
        for i in range(0, len(ids), chunk_size):
            chunk = ids[i:i + chunk_size]
            batch = await asyncio.gather(*[_fetch(uid) for uid in chunk], return_exceptions=True)
            all_results.extend(r for r in batch if isinstance(r, dict) and r)

        parsed = self.parse(all_results)
        if parsed:
            await self.store(parsed)
        self.logger.info("[%s] 库存同步完成: %s 条", self.shop.shop_id, len(parsed))
        return len(parsed)

    async def sync_by_id(self, user_product_id: str) -> dict | None:
        data = await self.stock(user_product_id)
        import os
        os.makedirs("resource/mercado", exist_ok=True)
        with open(f"resource/mercado/stock_{self.shop.shop_id}_{user_product_id}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data
