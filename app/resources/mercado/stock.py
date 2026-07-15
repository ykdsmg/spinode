"""
Mercado stock资源:请求/解析/存储/同步。
"""
import asyncio
from app.db.manager import DBManager
from aiolimiter import AsyncLimiter
from datetime import datetime
from app.platform.MercadoShop import MercadoShop
from typing import Dict



class Stock:
    """stock资源。"""

    def __init__(self, shop: MercadoShop):
        self.shop = shop


    def parsed_stock(self, resp: Dict) -> Dict:

        upsert_date = datetime.now().strftime("%Y-%m-%d")

        if not resp:
            return {}

        selling_address     = None
        meli_facility       = None
        seller_warehouse    = None

        for location in resp.get('locations') or []:
            type = location.get('type')
            if type == 'selling_address':
                selling_address     = location.get('quantity')
            if type == 'meli_facility':
                meli_facility       = location.get('quantity')
            if type == 'seller_warehouse':
                seller_warehouse    = location.get('quantity')
        return {
            "seller_id":        resp.get('user_id'),
            "upsert_date":      upsert_date,
            "user_product_id":  resp.get('id'),
            "selling_address":  selling_address,
            "meli_facility":    meli_facility,
            "seller_warehouse": seller_warehouse,
        }


    async def get_stock(self, USER_PRODUCT_ID: str, limiter: AsyncLimiter | None = None) -> dict:

        resp = await self.shop.request(
            method="GET",
            url=f"/user-products/{USER_PRODUCT_ID}/stock",
            headers={
                "Content-Type": "application/json",
            },
            limiter=limiter,
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


    async def sync_stock(self, limiter: AsyncLimiter):

        seller_id = self.shop.seller_id
        user_product_ids = await DBManager.select("SELECT DISTINCT user_product_id FROM mercado_product WHERE seller_id = %s AND user_product_id IS NOT NULL", [seller_id])

        tasks = []
        for item in user_product_ids:
            user_product_id = item['user_product_id']
            tasks.append(self.get_stock(user_product_id,limiter))

        if tasks:
            stock_rows = []
            resps = await asyncio.gather(*tasks)
            for resp in resps:
                if isinstance(resp, Exception):
                    continue
                stock_rows.append(self.parsed_stock(resp))
            await DBManager.upsert("mercado_product_stock", stock_rows, ["seller_id","user_product_id"])
