"""Mercado 商品资源: ItemSearch / ItemInfo / Variations 请求 / 解析 / 存储 / 同步。

全量同步流程:
  1. ItemSearch 分页拉取所有 item_id
  2. 按 20 个一批并发生 ItemInfo
  3. 解析为 MercadoProduct + Image + Attribute 三组数据
  4. 按 (seller_id, item_id, variation_id) 唯一键 upsert

Variations 同步: 查 mercado_product 中已有 variation 的商品, 并发生 Variations 接口拉取属性。
"""

from __future__ import annotations

import asyncio
import json

from aiolimiter import AsyncLimiter

from app.core.converters import (
    as_list,
    parse_datetime,
    safe_get,
    to_str,
    join_csv,
    to_json_str,
)
from app.db import repository
from app.http.client import HttpClient
from app.platform.base import Resource, Shop
from app.platforms.mercado.config import MercadoClient
from app.platforms.mercado.schemas import (
    MercadoProduct,
    MercadoProductImage,
    MercadoProductAttribute,
)


class ProductResource(Resource):
    """商品资源。"""

    def __init__(self, shop: "Shop") -> None:
        super().__init__(shop)
        self._item_search_limiter = AsyncLimiter(30, 10)

    # ── endpoints ──────────────────────────────────────

    async def _item_search(self, limit: int = 100, offset: int = 0) -> dict:
        """GET /users/{user_id}/items/search"""
        await self.shop.credential.ensure_valid()
        token = self.shop.credential.data.get("access_token", "")
        user_id = self.shop.credential.data.get("user_id", "")
        params = {"limit": str(limit), "offset": str(offset)}
        url = f"{self.shop.platform.settings.base_url}/users/{user_id}/items/search"
        headers = {"Authorization": f"Bearer {token}"}
        async with HttpClient(timeout=50, limiter=self._item_search_limiter) as client:
            resp = await client.request("GET", url, headers=headers, params=params)
        return await self._handle(resp)

    async def _item_info(self, ids: str) -> list[dict]:
        """GET /items/?ids=id1,id2,... (最多 20 个)"""
        client = MercadoClient(self.shop)
        return await client.get(f"/items/?ids={ids}")

    async def _variations(self, item_id: str, variation_id: str) -> dict:
        """GET /items/{item_id}/variations/{variation_id}"""
        client = MercadoClient(self.shop)
        return await client.get(f"/items/{item_id}/variations/{variation_id}")

    async def _handle(self, resp: "ApiResponse") -> dict:  # type: ignore
        if resp.status != 200:
            text = await resp.text()
            raise RuntimeError(f"Mercado API 请求失败: {resp.status}\n{text}")
        return await resp.json()

    # ── parse ──────────────────────────────────────────

    def parse_product(self, raw_list: list[dict]) -> list[dict]:
        """解析 ItemInfo[] → 商品散列表 (主表 + images + attributes)。"""
        seller_id = int(self.shop.shop_id)
        result: list[dict] = []

        for item in raw_list:
            if item.get("code") != 200:
                continue
            body = item.get("body", {})
            if not body:
                continue

            base = {
                "seller_id": seller_id,
                "item_id": body.get("id"),
                "site_id": body.get("site_id"),
                "title": body.get("title"),
                "family_name": body.get("family_name"),
                "family_id": body.get("family_id"),
                "category_id": body.get("category_id"),
                "user_product_id": body.get("user_product_id"),
                "official_store_id": body.get("official_store_id"),
                "price": body.get("price"),
                "base_price": body.get("base_price"),
                "original_price": body.get("original_price"),
                "inventory_id": body.get("inventory_id"),
                "currency_id": body.get("currency_id"),
                "initial_quantity": body.get("initial_quantity"),
                "available_quantity": body.get("available_quantity"),
                "sold_quantity": body.get("sold_quantity"),
                "buying_mode": body.get("buying_mode"),
                "listing_type_id": body.get("listing_type_id"),
                "start_time": parse_datetime(body.get("start_time")),
                "stop_time": parse_datetime(body.get("stop_time")),
                "end_time": parse_datetime(body.get("end_time")),
                "expiration_time": parse_datetime(body.get("expiration_time")),
                "condition": body.get("condition"),
                "permalink": body.get("permalink"),
                "thumbnail": body.get("thumbnail"),
                "video_id": body.get("video_id"),
                "descriptions": to_json_str(body.get("descriptions")),
                "accepts_mercadopago": body.get("accepts_mercadopago"),
                "status": body.get("status"),
                "sub_status": join_csv(body.get("sub_status")),
                "tags": join_csv(body.get("tags")),
                "warranty": body.get("warranty"),
                "catalog_product_id": body.get("catalog_product_id"),
                "domain_id": body.get("domain_id"),
                "seller_custom_field": body.get("seller_custom_field"),
                "parent_item_id": body.get("parent_item_id"),
                "differential_pricing": to_json_str(body.get("differential_pricing")),
                "automatic_relist": body.get("automatic_relist"),
                "health": to_json_str(body.get("health")),
                "catalog_listing": to_json_str(body.get("catalog_listing")),
                "item_relations": to_json_str(body.get("item_relations")),
                "channels": join_csv(body.get("channels")),
                "date_created": parse_datetime(body.get("date_created")),
                "last_updated": parse_datetime(body.get("last_updated")),
                # 子数据
                "pictures": [
                    {"seller_id": seller_id, "item_id": body.get("id"), "variation_id": "", "image_id": img.get("id"), "url": img.get("url")}
                    for img in body.get("pictures", [])
                ],
                "attributes": [
                    {"seller_id": seller_id, "item_id": body.get("id"), "variation_id": "", "attribute_id": a.get("id"), "attribute_name": a.get("name"), "value_id": a.get("value_id"), "value_name": a.get("value_name")}
                    for a in body.get("attributes", [])
                ],
                "variations": body.get("variations", []),
            }
            result.append(base)
        return result

    def _expand_variations(self, items: list[dict]) -> tuple[list[dict], list[dict]]:
        """展开变体: 将变体拆为独立行 (主表 + image 关联)。"""
        base_rows: list[dict] = []
        image_rows: list[dict] = []

        for p in items:
            variations = as_list(p.get("variations", []))
            if variations:
                main_pictures = p.get("pictures", [])
                for v in variations:
                    if not isinstance(v, dict):
                        continue
                    vid = str(v.get("id", ""))
                    base_rows.append({
                        **{k: v for k, v in p.items() if k not in ("pictures", "attributes", "variations")},
                        "variation_id": vid,
                        "price": v.get("price", p.get("price")),
                        "available_quantity": v.get("available_quantity"),
                        "sold_quantity": v.get("sold_quantity"),
                        "seller_custom_field": v.get("seller_custom_field"),
                        "catalog_product_id": v.get("catalog_product_id"),
                        "inventory_id": v.get("inventory_id"),
                        "item_relations": to_json_str(v.get("item_relations")),
                        "user_product_id": v.get("user_product_id"),
                    })
                    pic_ids = set(v.get("picture_ids") or [])
                    for img in main_pictures:
                        if img.get("image_id") in pic_ids:
                            img_copy = dict(img)
                            img_copy["variation_id"] = vid
                            image_rows.append(img_copy)
            else:
                base_rows.append({**p, "variation_id": ""})
                image_rows.extend(p.get("pictures", []))
        return base_rows, image_rows

    # ── store ──────────────────────────────────────────

    async def store(self, items: list[dict]) -> int:
        if not items:
            return 0
        seller_id = int(self.shop.shop_id)

        # 展开变体
        base_rows, image_rows = self._expand_variations(items)

        # 去重: 同一 (seller_id, item_id, variation_id) 只留一条
        seen: set[tuple] = set()
        deduped_base: list[dict] = []
        for r in base_rows:
            key = (r.get("seller_id"), r.get("item_id"), r.get("variation_id"))
            if key not in seen:
                seen.add(key)
                deduped_base.append(r)

        # 1) 主表
        models = [MercadoProduct(**{k: v for k, v in r.items() if k in MercadoProduct.model_fields}) for r in deduped_base]
        await repository.upsert_batch("mercado_product", models, ["seller_id", "item_id", "variation_id"])

        # 2) 查回 ID
        id_rows = await repository.select(
            "SELECT id, seller_id, item_id, variation_id FROM mercado_product WHERE seller_id = %s", [seller_id]
        )
        id_map: dict[tuple, int] = {}
        for r in id_rows:
            id_map[(int(r["seller_id"]), str(r["item_id"]), str(r["variation_id"]))] = int(r["id"])

        # 3) Image
        img_models: list[dict] = []
        for img in image_rows:
            mid = id_map.get((int(img.get("seller_id", seller_id)), str(img.get("item_id")), str(img.get("variation_id", ""))))
            if mid:
                img["main_id"] = mid
                img_models.append(img)
        if img_models:
            await repository.upsert_batch("mercado_product_image", img_models, ["main_id", "image_id"])

        # 4) Attribute
        attr_rows: list[dict] = []
        for p in items:
            for attr in p.get("attributes", []):
                mid = id_map.get((int(seller_id), str(p.get("item_id")), str(attr.get("variation_id", ""))))
                if mid:
                    attr["main_id"] = mid
                    attr_rows.append(attr)
        if attr_rows:
            await repository.upsert_batch("mercado_product_attribute", attr_rows, ["main_id", "attribute_id"])

        return len(deduped_base)

    # ── sync ───────────────────────────────────────────

    async def sync(self, save_detail: bool = True) -> int:
        """全量同步该店铺所有商品。"""
        seller_id = int(self.shop.shop_id)

        # 步骤 1: 拉取所有 item_id
        self.logger.info("[%s] 开始拉取商品 ID 列表...", seller_id)
        all_ids: list[str] = []
        offset = 0
        limit = 100
        while True:
            data = await self._item_search(limit=limit, offset=offset)
            results = data.get("results", [])
            all_ids.extend(results)
            total = data.get("paging", {}).get("total", 0)
            offset += limit
            if offset >= total or not results:
                break
        self.logger.info("[%s] 共 %s 个商品 ID", seller_id, len(all_ids))

        # 步骤 2: 并发拉取详情
        chunks = [all_ids[i:i + 20] for i in range(0, len(all_ids), 20)]
        all_products: list[dict] = []

        async def _fetch_batch(ids_chunk: list[str]) -> list[dict]:
            ids_str = ",".join(ids_chunk)
            try:
                return await self._item_info(ids_str)
            except Exception as e:
                self.logger.warning("商品详情批次失败: %s", e)
                return []

        for i in range(0, len(chunks), 10):
            batch_chunks = chunks[i:i + 10]
            results = await asyncio.gather(*[_fetch_batch(c) for c in batch_chunks], return_exceptions=True)
            for r in results:
                if isinstance(r, list):
                    all_products.extend(r)

        self.logger.info("[%s] 共获取 %s 个商品详情", seller_id, len(all_products))

        # 步骤 3: 解析 + 存储
        if all_products:
            parsed = self.parse_product(all_products)
            if save_detail:
                await self.store(parsed)
        return len(all_products)

    async def sync_by_ids(self, item_ids: list[str], save_detail: bool = True) -> int:
        """按商品 ID 列表拉取详情。"""
        chunks = [item_ids[i:i + 20] for i in range(0, len(item_ids), 20)]
        all_products: list[dict] = []
        for ch in chunks:
            try:
                all_products.extend(await self._item_info(",".join(ch)))
            except Exception as e:
                self.logger.warning("商品详情批次失败: %s", e)
        if all_products:
            parsed = self.parse_product(all_products)
            if save_detail:
                await self.store(parsed)
        return len(all_products)

    async def sync_by_id(self, item_id: str) -> dict | None:
        """按单个商品 ID 拉取详情并落盘调试。"""
        data = await self._item_info(item_id)
        parsed = self.parse_product(data)
        if parsed:
            await self.store(parsed)
        import os
        os.makedirs("resource/mercado", exist_ok=True)
        with open(f"resource/mercado/product_{self.shop.shop_id}_{item_id}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        return parsed[0] if parsed else None

    # ── Variations ──────────────────────────────────────

    def parse_variations(self, raw: list[dict]) -> list[dict]:
        """解析 Variations 接口返回 → 属性行列表。"""
        result: list[dict] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            attr_comb = as_list(item.get("attribute_combinations", []))
            attrs = as_list(item.get("attributes", []))
            all_attrs = attrs + attr_comb
            for a in all_attrs:
                result.append({
                    "seller_id": item.get("seller_id"),
                    "item_id": item.get("item_id"),
                    "variation_id": str(item.get("variation_id", "")),
                    "main_id": item.get("main_id"),
                    "attribute_id": a.get("id"),
                    "attribute_name": a.get("name"),
                    "value_id": a.get("value_id"),
                    "value_name": a.get("value_name"),
                })
        return result

    async def store_variations(self, items: list[dict]) -> int:
        if not items:
            return 0
        await repository.upsert_batch("mercado_product_attribute", items, ["main_id", "attribute_id"])
        return len(items)

    async def sync_variations(self) -> int:
        """同步有变体的商品的 Variation 属性。"""
        rows = await repository.select(
            "SELECT id, item_id, variation_id FROM mercado_product WHERE seller_id = %s AND variation_id <> ''",
            [int(self.shop.shop_id)],
        )
        if not rows:
            return 0

        tasks = []
        for r in rows:
            tasks.append((r["id"], r["item_id"], r["variation_id"]))

        async def _fetch_one(main_id, item_id, variation_id):
            try:
                data = await self._variations(item_id, variation_id)
                data["seller_id"] = int(self.shop.shop_id)
                data["main_id"] = main_id
                data["item_id"] = item_id
                data["variation_id"] = variation_id
                return data
            except Exception:
                return None

        results = await asyncio.gather(*[_fetch_one(a, b, c) for a, b, c in tasks], return_exceptions=True)
        valid = [r for r in results if isinstance(r, dict) and r]
        parsed = self.parse_variations(valid)
        if parsed:
            await self.store_variations(parsed)
        self.logger.info("[%s] Variations 同步: %s 条", self.shop.shop_id, len(parsed))
        return len(parsed)
