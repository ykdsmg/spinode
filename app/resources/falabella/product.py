"""Falabella 商品资源: GetProducts 请求 / 解析 / 存储 / 同步"""

from app.db.manager import DBManager
from app.platform.FalabellaShop import FalabellaShop
from typing import Dict

class Product:
    """商品资源。"""

    def __init__(self, shop: FalabellaShop):
        self.shop = shop

    def parse(self, resp: Dict):
        """解析商品响应。"""
        if not resp:
            return {}

        data = ((resp.get("Body") or {}).get("Products") or {}).get("Product")

        if not data:
            return {}
        else:
            pro_info_list = []
            ima_info_list = []
            bus_info_list = []
            abt_info_list = []
            if isinstance(data, dict):
                data = [data]
            for Product in data:
                seller_id = self.shop.seller_id
                seller_sku = Product.get("SellerSku")
                shop_sku = Product.get("ShopSku")

                Images = (Product.get("Images") or {}).get("Image", []) or []
                BusinessUnit = (Product.get("BusinessUnits") or {}).get(
                    "BusinessUnit"
                ) or {}
                ProductData = Product.get("ProductData") or {}
                pro_info = {
                    "SellerSku": seller_sku,
                    "SellerId": seller_id,
                    "ShopSku": shop_sku,
                    "Name": Product.get("Name"),
                    "Variation": Product.get("Variation"),
                    "ProductId": Product.get("ProductId"),
                    "ParentSku": Product.get("ParentSku"),
                    "Url": Product.get("Url"),
                    "ContentScore": Product.get("ContentScore"),
                    "Description": Product.get("Description"),
                    "TaxClass": Product.get("TaxClass"),
                    "Brand": Product.get("Brand"),
                    "PrimaryCategory": Product.get("PrimaryCategory"),
                    "QCStatus": Product.get("QCStatus"),
                    "PrimaryCategoryId": Product.get("PrimaryCategoryId"),
                }
                ima_info = [
                    {
                        "RBProductId": None,
                        "SellerSku": seller_sku,
                        "ShopSku": shop_sku,
                        "SellerId": seller_id,
                        "ImageUrl": url,
                        "SortOrder": i + 1,
                        "IsMain": 1 if i == 0 else 0,
                    }
                    for i, url in Images
                ]
                bus_info = {
                    "RBProductId": None,
                    "SellerSku": seller_sku,
                    "SellerId": seller_id,
                    "ShopSku": shop_sku,
                    "BusinessUnit": BusinessUnit.get("BusinessUnit"),
                    "OperatorCode": BusinessUnit.get("OperatorCode"),
                    "Price": BusinessUnit.get("Price") or None,
                    "SpecialPrice": BusinessUnit.get("SpecialPrice") or None,
                    "SpecialFromDate": BusinessUnit.get("SpecialFromDate") or None,
                    "SpecialToDate": BusinessUnit.get("SpecialToDate") or None,
                    "Status": BusinessUnit.get("Status"),
                    "IsPublished": BusinessUnit.get("IsPublished"),
                }
                abt_info = [
                    {
                        "RBProductId": None,
                        "SellerSku": seller_sku,
                        "ShopSku": shop_sku,
                        "SellerId": seller_id,
                        "AttributeName": k,
                        "AttributeValue": y,
                    }
                    for k, y in ProductData.items()
                ]
                pro_info_list.append(pro_info)
                bus_info_list.append(bus_info)
                ima_info_list.extend(ima_info)
                abt_info_list.extend(abt_info)
            return {
                "pro_info": pro_info_list,
                "ima_info": ima_info_list,
                "bus_info": bus_info_list,
                "abt_info": abt_info_list,
            }

    async def save(self, resp: Dict):
        if not resp:
            return

        pro_info = resp.get("pro_info") or []
        ima_info = resp.get("ima_info") or []
        bus_info = resp.get("bus_info") or []
        abt_info = resp.get("abt_info") or []

        await DBManager.upsert(
            "falabella_product", pro_info, ["SellerSku", "ShopSku", "SellerId"]
        )

        id_map = {
            (item["SellerSku"], item["ShopSku"], item["SellerId"]): item["ID"]
            for item in await DBManager.select(
                "SELECT ID,SellerSku,ShopSku,SellerId FROM falabella_product WHERE SellerId = %s",
                [self.shop.seller_id],
            )
        }

        for item in ima_info:
            item["RBProductId"] = id_map.get(
                (item["SellerSku"], item["ShopSku"], item["SellerId"])
            )
            item.pop("SellerSku")
            item.pop("ShopSku")
            item.pop("SellerId")
        await DBManager.upsert(
            "falabella_product_image", ima_info, ["RBProductId", "SortOrder"]
        )

        for item in bus_info:
            item["RBProductId"] = id_map.get(
                (item["SellerSku"], item["ShopSku"], item["SellerId"])
            )
            item.pop("SellerSku")
            item.pop("ShopSku")
            item.pop("SellerId")
        await DBManager.upsert(
            "falabella_product_business_unit", bus_info, ["RBProductId"]
        )

        for item in abt_info:
            item["RBProductId"] = id_map.get(
                (item["SellerSku"], item["ShopSku"], item["SellerId"])
            )
            item.pop("SellerSku")
            item.pop("ShopSku")
            item.pop("SellerId")
        await DBManager.upsert(
            "falabella_product_attribute", abt_info, ["RBProductId", "AttributeName"]
        )

    def get_product(self, search: Dict):

        resp = self.shop.request(
            method="GET",
            action="GetProducts",
            params=search,
        )
        return resp

    async def sync_products(self, search: Dict):
        """全量同步商品 (自动翻页)。返回同步总数。"""
        limit = 1000
        offset = 0
        count = None
        while count is None or offset < count:
            search.update({"Limit": limit, "Offset": offset})

            resp = self.get_product(search)
            if not resp:
                continue
            else:
                await self.save(self.parse(resp))
