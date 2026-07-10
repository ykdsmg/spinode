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


    async def item(self,ids: str):


        resp = await self.shop.request(
            method="GET",
            url="/items/",
            headers={
                "Content-Type": "application/json",
            },
            params={"ids": ids}
        )

        return resp


    async def variation(self,ITEM_ID: str,VARIATION_ID: str):


        resp = await self.shop.request(
            method="GET",
            url=f"/items/{ITEM_ID}/variations/{VARIATION_ID}",
            headers={
                "Content-Type": "application/json",
            }
        )

        return resp
