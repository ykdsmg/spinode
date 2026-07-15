"""Falabella 库存资源: GetStock 请求 / 解析 / 存储 / 同步。"""

from datetime import datetime
from app.db.manager import DBManager
from app.platform.FalabellaShop import FalabellaShop
from typing import Dict


class Stock:
    """商品资源。"""

    def __init__(self, shop: FalabellaShop):
        self.shop = shop

    def parse(self, resp: dict):
        """解析商品响应。"""
        if not resp:
            return {}

        body = resp.get("SuccessResponse", {}).get("Body") or {}

        data = body.get("Stocks") or {}

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

    async def get_stocks(self, search: Dict):

        resp = self.shop.request(
            method="GET",
            action="GetStock",
            params=search,
        )

        return resp

    async def save(self, data: dict):
        if not data:
            return

        SellerWarehouses = data.get("SellerWarehouses") or []
        FulfillmentWarehouses = data.get("FulfillmentWarehouses") or []
        await DBManager.upsert("falabella_stock_sellerwarehouses", SellerWarehouses, ['SellerId','FacilityID','Sku'])
        await DBManager.upsert("falabella_stock_fulfillmentwarehouses", FulfillmentWarehouses, ['SellerId','WarehouseId','Sku'])

    async def sync_stocks(self, search: Dict):
        """全量同步商品 (自动翻页)。返回同步总数。"""
        limit   = search.get("Limit")  or 1000
        offset  = search.get("Offset") or 0
        count   = None

        while count is None or False:

            search.update({"Limit": limit, "Offset": offset})

            resp = await self.get_stocks(search)

            if count is None:
                count = 0

            if not resp:
                continue
            else:
                resp = self.parse(resp)
                if resp:
                    await self.save(resp)
            offset += limit
