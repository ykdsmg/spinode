"""
Mercado product 资源:请求/解析/存储/同步。
"""
import asyncio
from app.db.manager import DBManager
from app.platform.MercadoShop import MercadoShop
from typing import Dict, List
from app.core.converters import _trim, _str, _lstr


class Product:
    """product资源。"""

    def __init__(self, shop: MercadoShop):
        self.shop = shop


    def parse_product(self, data: List):
        product_rows = []
        picture_rows = []
        attribute_rows = []
        seller_id = self.shop.seller_id
        for item in data:
            if item.get('code') != 200:
                continue
            body = item['body']
            pictures = body.get('pictures') or []
            attributes = body.get('attributes') or []
            variations = body.get('variations') or [{}]
            product_row = {
                "item_id":                              body.get('id'),
                "site_id":                              body.get('site_id'),
                "title":                                body.get('title'),
                "family_name":                          body.get('family_name'),
                "family_id":                            body.get('family_id'),
                "seller_id":                            body.get('seller_id'),
                "category_id":                          body.get('category_id'),
                "user_product_id":                      body.get('user_product_id'),
                "official_store_id":                    body.get('official_store_id'),
                "price":                                body.get('price'),
                "base_price":                           body.get('base_price'),
                "original_price":                       body.get('original_price'),
                "inventory_id":                         body.get('inventory_id'),
                "currency_id":                          body.get('currency_id'),
                "initial_quantity":                     body.get('initial_quantity'),
                "available_quantity":                   body.get('available_quantity'),
                "sold_quantity":                        body.get('sold_quantity'),
                "buying_mode":                          body.get('buying_mode'),
                "listing_type_id":                      body.get('listing_type_id'),
                "start_time":                           _trim(body.get('start_time')),
                "stop_time":                            _trim(body.get('stop_time')),
                "end_time":                             _trim(body.get('end_time')),
                "expiration_time":                      _trim(body.get('expiration_time')),
                "condition":                            body.get('condition'),
                "permalink":                            body.get('permalink'),
                "thumbnail_id":                         body.get('thumbnail_id'),
                "thumbnail":                            body.get('thumbnail'),
                "video_id":                             body.get('video_id'),
                "descriptions":                         _lstr(body.get('descriptions')),
                "accepts_mercadopago":                  body.get('accepts_mercadopago'),
                # "shipping":                             body.get('shipping'),
                # "international_delivery_mode":          body.get('international_delivery_mode'),
                # "seller_address":                       body.get('seller_address'),
                # "seller_contact":                       body.get('seller_contact'),
                # "location":                             body.get('location'),
                # "geolocation":                          body.get('geolocation'),
                # "coverage_areas":                       body.get('coverage_areas'),
                # "warnings":                             body.get('warnings'),
                # "listing_source":                       body.get('listing_source'),
                # "variations":                           body.get('variations'),
                # "deal_ids":                             body.get('deal_ids'),
                # "item_relations":                       body.get('item_relations'),
                # "channels":                             body.get('channels'),
                "status":                               body.get('status'),
                "sub_status":                           _lstr(body.get('sub_status')),
                "tags":                                 _lstr(body.get('tags')),
                "warranty":                             body.get('warranty'),
                "catalog_product_id":                   body.get('catalog_product_id'),
                "domain_id":                            body.get('domain_id'),
                "seller_custom_field":                  body.get('seller_custom_field'),
                "parent_item_id":                       body.get('parent_item_id'),
                "differential_pricing":                 body.get('differential_pricing'),
                "automatic_relist":                     body.get('automatic_relist'),
                "date_created":                         _trim(body.get('date_created')),
                "last_updated":                         _trim(body.get('last_updated')),
                "health":                               body.get('health'),
                "catalog_listing":                      body.get('catalog_listing'),
            }

            for variation in variations
                if variation:
                    variation_row = {
                        "variation_id":         _str(variation.get('id')),
                        "price":                variation.get('price'),
                        "available_quantity":   variation.get('available_quantity'),
                        "sold_quantity":        variation.get('sold_quantity'),
                        "seller_custom_field":  variation.get('seller_custom_field'),
                        "catalog_product_id":   variation.get('catalog_product_id'),
                        "inventory_id":         variation.get('inventory_id'),
                        "item_relations":       _str(variation.get('item_relations')),
                        "user_product_id":      variation.get('user_product_id'),
                    }
                    product_rows.append(product_row | variation_row)
                    variation_picture_ids = variation.get("picture_ids") or []
                    for picture in pictures:
                        image_id = _str(picture.get('id'))
                        curr_image = {
                            "seller_id":        seller_id,
                            "item_id":          _str(body.get('id')),
                            "variation_id":     "",
                            "image_id":         image_id,
                            "url":              picture.get('url'),
                        }
                        if image_id in variation_picture_ids:
                            picture_rows.append(curr_image)

                else:
                    variation_row = {
                        "variation_id": "",
                    }
                    product_rows.append(product_row | variation_row)
                    for picture in pictures:
                        image_id = _str(picture.get('id'))
                        curr_image = {
                            "seller_id":        seller_id,
                            "item_id":          _str(body.get('id')),
                            "variation_id":     "",
                            "image_id":         image_id,
                            "url":              picture.get('url'),
                        }
                        picture_rows.append(curr_image)
                    for attribute in attributes:
                        attribute_rows.append({
                            "seller_id":        seller_id,
                            "item_id":          _str(item.get('id')),
                            "variation_id":     "",
                            "attribute_id":     attribute.get('id'),
                            "attribute_name":   attribute.get('name'),
                            "value_id":         attribute.get('value_id'),
                            "value_name":       attribute.get('value_name'),
                        })
        return{
            "product_rows": product_rows,
            "picture_rows": picture_rows,
            "attribute_rows": attribute_rows,
        }


    def parse_variations(self, data: Dict | List):

        if not data:
            return []

        if isinstance(data, dict):
            data = [data]
        seller_id = self.shop.seller_id
        v_rows = []
        for item in data:
            attribute_combinations = item.get('attribute_combinations') or []
            attributes             = item.get('attributes') or []
            for attribute in attributes + attribute_combinations:
                v_row = {
                    "seller_id":                seller_id,
                    "main_id":                  item.get('id'),
                    "item_id":                  item.get('item_id'),
                    "variation_id":             str(item.get('id')),
                    "attribute_id":             attribute.get('id'),
                    "attribute_name":           attribute.get('name'),
                    "value_id":                 attribute.get('value_id'),
                    "value_name":               attribute.get('value_name'),
                }
                v_rows.append(v_row)

        return v_rows


    async def save_product(self, data: Dict):
        if not data:
            return

        product_rows = data.get('product_rows') or []
        picture_rows = data.get('picture_rows') or []
        attribute_rows = data.get('attribute_rows') or []

        await DBManager.upsert("mercado_product", product_rows, ["seller_id","item_id","variation_id"])

        id_map = {
            (item['item_id'],item['variation_id']): item['id']
            for item in await DBManager.select("SELECT id,item_id,variation_id FROM mercado_product WHERE seller_id = %s", [self.shop.seller_id])
        }

        for item in picture_rows:
            item["main_id"] = id_map.get((item['item_id'], item['variation_id']))
        for item in attribute_rows:
            item["main_id"] = id_map.get((item['item_id'], item['variation_id']))

        await DBManager.upsert("mercado_product_image", picture_rows, ["main_id","image_id"])
        await DBManager.upsert("mercado_product_attribute", attribute_rows, ["main_id","attribute_id"])


    async def save_variation(self, data: List):
        if not data:
            return
        if not isinstance(data, list):
            data = [data]
        await DBManager.upsert("mercado_product_variation", data, ["main_id","variation_id"])


    async def get_product(self,ids: str):
        resp = await self.shop.request(
            method="GET",
            url=f"/items/",
            headers={
                "Content-Type": "application/json",
            },
            params={
                "ids": ids,
            }
        )
        return resp


    async def get_variation(self, ITEM_ID: str, VARIATION_ID: str):
        resp = await self.shop.request(
            method="GET",
            url=f"/items/{ITEM_ID}/variations/{VARIATION_ID}",
            headers={
                "Content-Type": "application/json",
            }
        )
        return resp


    async def iteam_search(self,  limit: int = 100, offset: int = 0):

        seller_id = self.shop.seller_id

        resp = await self.shop.request(
            method="GET",
            url=f"/users/{seller_id}/items/search",
            headers={
                "Content-Type": "application/json",
            },
            params={
                "limit": limit,
                "offset": offset,
            }
        )

        return resp


    async def sync_product(self):

        limit = 100
        offset = 0
        total = None

        ids = []

        while total is None or offset < total:
            resp = await self.iteam_search(limit=limit, offset=offset)

            if total is None:
                total = resp.get('paging',{}).get('total', None)
                if total is None:
                    break
            ids.extend(resp.get('results') or [])
            offset += limit

        ids_list = [ids[i:i+20] for i in range(0, len(ids), 20)]

        tasks = []
        for item in ids_list:
            item_str = _lstr(item)
            if item_str:
                tasks.append(self.get_product(item_str))
        await asyncio.gather(*tasks)

        products = []
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    continue
                if isinstance(result, Dict):
                    products.extend(result)
        parsed = self.parse_product(products)
        await self.save_product(parsed)


    async def sync_variation(self):

        seller_id = self.shop.seller_id

        v_ids = await DBManager.select("SELECT id,item_id,variation_id FROM mercado_product WHERE seller_id = % AND variation_id <> ''", [seller_id])

        tasks = []
        for v_id in v_ids:
            tasks.append(self.get_variation(v_id['item_id'], v_id['variation_id']))
        await asyncio.gather(*tasks)

        variations = []
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for v_id, result in zip(v_ids, results):
                if isinstance(result, Exception):
                    continue
                if isinstance(result, Dict):
                    result.update({
                        'main_id': v_id['id'],
                        'item_id': v_id['item_id'],
                    })
                    variations.append(result)

        parsed = self.parse_variations(variations)
        await self.save_variation(parsed)
