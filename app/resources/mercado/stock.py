"""
Mercado stock资源:请求/解析/存储/同步。
"""
import asyncio
from app.db.manager import DBManager
from datetime import datetime
from app.platform.MercadoShop import MercadoShop
from typing import Dict, List



class Stock:
    """stock资源。"""

    def __init__(self, shop: MercadoShop):
        self.shop = shop


    def parsed_stock(self, resp: Dict | List) -> List:

        upsert_date = datetime.now().strftime("%Y-%m-%d")
        if isinstance(resp, Dict):
            resp = [resp]
        stock_rows = []
        for item in resp:
            selling_address     = None
            meli_facility       = None
            seller_warehouse    = None

            for location in item.get('locations'):
                type = location.get('type')
                if type == 'selling_address':
                    selling_address     = location.get('quantity')
                if type == 'meli_facility':
                    meli_facility       = location.get('quantity')
                if type == 'seller_warehouse':
                    seller_warehouse    = location.get('quantity')
            stock_rows.append({
                "seller_id":        item.get('user_id'),
                "upsert_date":      upsert_date,
                "user_product_id":  item.get('id'),
                "selling_address":  selling_address,
                "meli_facility":    meli_facility,
                "seller_warehouse": seller_warehouse,
            })
        return stock_rows


    async def get_stock(self, USER_PRODUCT_ID: str) -> dict:

        resp = await self.shop.request(
            method="GET",
            url=f"/user-products/{USER_PRODUCT_ID}/stock",
            headers={
                "Content-Type": "application/json",
            }
        )

        return resp


    async def get_fulfillment_stock(self, INVENTORY_ID: str) -> dict:

        resp = await self.shop.request(
            method="GET",
            url=f"/inventories/{INVENTORY_ID}/stock/fulfillment",
            headers={
                "Content-Type": "application/json",
            }
        )

        return resp


    async def sync_stock(self,):
        pass
