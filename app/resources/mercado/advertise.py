"""Mercado 广告资源: Orders 请求 / 解析 / 存储 / 同步"""
import asyncio
from app.db.manager import DBManager
from app.platform.MercadoShop import MercadoShop
from typing import Dict, List
from app.core.converters import _trim, _json



class Advertise:

    def __init__(self, shop: MercadoShop):
        self.shop = shop


    async def get_advertisers(self, PRODUCT_ID: str):

        resp = await self.shop.request(
            method="GET",
            url=f"/advertising/advertisers?product_id={PRODUCT_ID}",
            headers={
                "Content-Type": "application/json",
                "Api-Version":"1"
            }
        )

        return resp


    async def get_adgroups(self, ADVERTISER_SITE_ID: str, ADVERTISER_ID: str, limit: int = 100, offset: int = 0, DATA_AT: str | None = None, DATA_TO: str | None = None):

        metrics = "metrics=CLICKS,PRINTS,COST,CPC,CTR,DIRECT_AMOUNT,INDIRECT_AMOUNT,TOTAL_AMOUNT,DIRECT_UNITS_QUANTITY,INDIRECT_UNITS_QUANTITY,UNITS_QUANTITY,DIRECT_ITEMS_QUANTITY,INDIRECT_ITEMS_QUANTITY,ADVERTISING_ITEMS_QUANTITY,ORGANIC_UNITS_QUANTITY,ORGANIC_UNITS_AMOUNT,ORGANIC_ITEMS_QUANTITY,ACOS"

        if DATA_AT and DATA_TO:
            data_filter = f"date_from={DATA_AT}&date_to={DATA_TO}"
        else:
            data_filter = ""
            metrics = ""

        resp = await self.shop.request(
            method="GET",
            url=f"/advertising/{ADVERTISER_SITE_ID}/advertisers/{ADVERTISER_ID}/product_ads/ad_groups/search?{data_filter}&limit={limit}&offset={offset}&{metrics}",
            headers={
                "Content-Type": "application/json",
                "Api-Version":"2"
            }
        )

        return resp


    async def get_adgroup_details(self, ADVERTISER_SITE_ID: str, AD_GROUP_ID: str, DATA_AT: str, DATA_TO: str):

        metrics = "metrics=CLICKS,PRINTS,COST,CPC,CTR,DIRECT_AMOUNT,INDIRECT_AMOUNT,TOTAL_AMOUNT,DIRECT_UNITS_QUANTITY,INDIRECT_UNITS_QUANTITY,UNITS_QUANTITY,DIRECT_ITEMS_QUANTITY,INDIRECT_ITEMS_QUANTITY,ADVERTISING_ITEMS_QUANTITY,ORGANIC_UNITS_QUANTITY,ORGANIC_UNITS_AMOUNT,ORGANIC_ITEMS_QUANTITY,ACOS"

        resp = await self.shop.request(
            method="GET",
            url=f"/advertising/{ADVERTISER_SITE_ID}/product_ads/ad_groups/{AD_GROUP_ID}?date_from={DATA_AT}&date_to={DATA_TO}&aggregation_type=daily&{metrics}",
            headers={
                "Content-Type": "application/json",
            }
        )

        return resp


    async def sync_advertisers(self, PRODUCT_ID: str):

        resp = await self.get_advertisers(PRODUCT_ID)

        advertisers = resp.get("advertisers", [])

        parsed = []

        for advertiser in advertisers:
            parsed.append({
                "seller_id":        self.shop.seller_id,
                "advertiser_id":    advertiser.get("advertiser_id"),
                "site_id":          advertiser.get("site_id"),
                "advertiser_name":  advertiser.get("advertiser_name"),
                "account_name":     advertiser.get("account_name"),
            })
        await DBManager.upsert("mercado_advertiser", parsed, conflict_cols=["seller_id", "advertiser_id"])


    async def sync_adgroups(self):

        advertisers = await self.get_advertisers("PADS")
        advertisers = advertisers.get("advertisers", [])


        for advertiser in advertisers:
            advertiser_id = advertiser.get("advertiser_id")
            site_id = advertiser.get("site_id")

            limit = 100
            offset = 0
            total = None

            while total is None or offset < total:
                resp = await self.get_adgroups(site_id, advertiser_id, limit, offset)

                if total is None:
                    total = int((resp.get("paging") or {}).get("total", 0))
                    if total == 0:
                        break

                data = resp.get("results") or []
                if not data:
                    break

                parsed = self.parse_adgroups(data)
                for item in parsed:
                    item["site_id"] = site_id
                await DBManager.upsert("mercado_adgroup", parsed, conflict_cols=["seller_id", "adgroup_id"])

                offset += limit


    async def sync_adgroup_details(self, data_at: str, data_to: str):
        seller_id = self.shop.seller_id

        adgroups = await DBManager.select("select id,site_id,adgroup_id from mercado_adgroup where seller_id = %s", [seller_id])

        task = []
        for adgroup in adgroups:
            adgroup_id = adgroup["adgroup_id"]
            site_id = adgroup["site_id"]
            task.append(self.get_adgroup_details(site_id, adgroup_id, data_at, data_to))

        results = await asyncio.gather(*task, return_exceptions=True)

        parsed_list = []
        for adgroup, result in zip(adgroups, results):
            if isinstance(result, Exception):
                continue
            if isinstance(result, dict):
                main_id = adgroup["id"]
                parsed = self.parse_adgroup_details(result, main_id)
                parsed_list.extend(parsed)

        await DBManager.upsert("mercado_adgroup_details", parsed_list,["main_id","ad_date"])


    def parse_adgroups(self, data: List) -> List:
        parsed = []
        seller_id = self.shop.seller_id
        for item in data:
            date_created = item.get("date_created")
            parsed.append({
                "seller_id":                seller_id,
                "adgroup_id":               item.get("id"),
                "channel":                  item.get("channel"),
                "catalog_listing":          item.get("catalog_listing"),
                "title":                    item.get("title"),
                "advertiser_id":            item.get("advertiser_id"),
                "ad_group_type":            item.get("ad_group_type"),
                "domain_id":                item.get("domain_id"),
                "official_store_id":        item.get("official_store_id"),
                "campaign_id":              item.get("campaign_id"),
                "original_advertiser_id":   item.get("original_advertiser_id"),
                "thumbnail":                item.get("thumbnail"),
                "date_created":             _trim(date_created),
                "ad_group_external_id":     item.get("ad_group_external_id"),
                "current_advertiser_id":    item.get("current_advertiser_id"),
                "sll":                      item.get("sll"),
                "brand_value_id":           item.get("brand_value_id"),
                "status":                   item.get("status"),
                "tags":                     _json(item.get("tags"))
            })
        return parsed


    def parse_adgroup_details(self, data: Dict, main_id: int) -> List:
        results = data.get("results") or []
        if not results:
            return []

        parsed = []
        for item in results:
            parsed.append({
                "main_id":                      main_id,
                "clicks":                       item.get("clicks"),
                "prints":                       item.get("prints"),
                "cost":                         item.get("cost"),
                "cpc":                          item.get("cpc"),
                "direct_amount":                item.get("direct_amount"),
                "indirect_amount":              item.get("indirect_amount"),
                "total_amount":                 item.get("total_amount"),
                "direct_units_quantity":        item.get("direct_units_quantity"),
                "indirect_units_quantity":      item.get("indirect_units_quantity"),
                "units_quantity":               item.get("units_quantity"),
                "direct_items_quantity":        item.get("direct_items_quantity"),
                "indirect_items_quantity":      item.get("indirect_items_quantity"),
                "advertising_items_quantity":   item.get("advertising_items_quantity"),
                "organic_units_quantity":       item.get("organic_units_quantity"),
                "organic_items_quantity":       item.get("organic_items_quantity"),
                "acos":                         item.get("acos"),
                "organic_units_amount":         item.get("organic_units_amount"),
                "ctr":                          item.get("ctr"),
                "ad_date":                      item.get("date"),
            })
        return parsed
