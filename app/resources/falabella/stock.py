"""Falabella 库存资源: GetStock 请求 / 解析 / 存储 / 同步。"""

from datetime import datetime

from api.schemas import FLStockSearch

from app.db.manager import DBManager
from app.http.client import HttpClient
from app.platform.FalabellaShop import FalabellaShop


class Stock:
    """商品资源。"""

    def __init__(self, shop: FalabellaShop, client: HttpClient):
        self.shop = shop
        self.client = client or HttpClient(async_mode=False)

    def parse(self, resp: dict | None):
        """解析商品响应。"""
        if not resp:
            return None

        data = (resp.get("Body") or {}).get("Stocks") or {}

        SellerWarehouses = data.get("SellerWarehouses") or []
        FulfillmentWarehouses = data.get("FulfillmentWarehouses") or []
        UpsertDate = datetime.now().strftime("%Y-%m-%d")
        seller_id = self.shop.seller_id
        for item in SellerWarehouses:
            item["SellerId"] = seller_id
            item["UpsertDate"] = UpsertDate
            item["FacilityID"] = item.get("FacilityID")
            item["Quantity"] = item.get("Quantity") or 0
            item["SellerWarehouseId"] = item.get("SellerWarehouseId")
            item["Sku"] = item.get("Sku")

        for item in FulfillmentWarehouses:
            item["SellerId"] = seller_id
            item["UpsertDate"] = UpsertDate
            item["WarehouseId"] = item.get("WarehouseId")
            item["Quantity"] = item.get("Quantity") or 0
            item["WarehouseName"] = item.get("WarehouseName")
            item["Sku"] = item.get("Sku")

        return {
            "SellerWarehouses": SellerWarehouses,
            "FulfillmentWarehouses": FulfillmentWarehouses,
        }

    async def save(self, data: dict):
        if not data:
            return

        SellerWarehouses = data.get("SellerWarehouses") or []
        FulfillmentWarehouses = data.get("FulfillmentWarehouses") or []
        await DBManager.upsert(
            "falabella_stock_sellerwarehouses", SellerWarehouses, ["SellerId", "Sku"]
        )
        await DBManager.upsert(
            "falabella_stock_fulfillmentwarehouses",
            FulfillmentWarehouses,
            ["SellerId", "Sku"],
        )

    async def fetch(self, search: FLStockSearch):
        params = {k: v for k, v in search.model_dump().items() if v is not None}

        url = self.shop._build_url("GetStock", params)
        headers = self.shop._build_headers()
        try:
            resp = await self.client.request_sync(
                method="GET", url=url, headers=headers
            )
            return resp.json()
        except Exception as e:
            return None

    async def sync_stock(self, search: FLStockSearch):
        """全量同步商品 (自动翻页)。返回同步总数。"""
        limit = 1000
        offset = 0
        count = 0
        first = True

        while first or (limit - count == 0):
            search.Limit = limit
            search.Offset = offset

            if first:
                first = False

            resp = await self.fetch(search)
            if not resp:
                continue
            else:
                resp = self.parse(resp)

                if resp:
                    count += len(resp.get("SellerWarehouses") or []) + len(
                        resp.get("FulfillmentWarehouses") or []
                    )
                    await self.save(resp)
