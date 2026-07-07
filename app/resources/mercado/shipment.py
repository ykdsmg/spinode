"""Mercado 货运资源: Shipment/History/Sla/Labels/Packs 请求/解析/存储/同步。

订单同步完成后调用 sync_shipments 拉取 shipment + sla 并存储。
"""

from __future__ import annotations

import asyncio

from app.core.converters import parse_datetime, join_csv
from app.db import repository
from app.http.client import HttpClient
from app.platform.base import Resource, Shop
from app.platforms.mercado.config import MercadoClient


class ShipmentResource(Resource):
    """货运资源。"""

    def __init__(self, shop: "Shop") -> None:
        super().__init__(shop)

    async def _handle(self, resp) -> dict | None:
        if resp is None:
            return None
        if resp.status != 200:
            self.logger.warning("Mercado API 失败: %s", resp.status)
            return None
        return await resp.json()

    async def _get_headers(self) -> dict:
        await self.shop.credential.ensure_valid()
        token = self.shop.credential.data.get("access_token", "")
        return {"Authorization": f"Bearer {token}"}

    # ── fetch endpoints ─────────────────────────────────

    async def shipment(self, shipment_id: str) -> dict | None:
        headers = await self._get_headers()
        headers["X-Format-New"] = "true"
        url = f"{self.shop.platform.settings.base_url}/shipments/{shipment_id}"
        async with HttpClient(timeout=30) as client:
            resp = await client.request("GET", url, headers=headers)
        return await self._handle(resp)

    async def shipment_sla(self, shipment_id: str) -> dict | None:
        try:
            client = MercadoClient(self.shop)
            return await client.get(f"/shipments/{shipment_id}/sla")
        except RuntimeError as e:
            self.logger.warning("Mercado API 失败: %s", e)
            return None

    async def packs(self, pack_id: str) -> dict | None:
        try:
            client = MercadoClient(self.shop)
            return await client.get(f"/packs/{pack_id}")
        except RuntimeError as e:
            self.logger.warning("Mercado API 失败: %s", e)
            return None

    # ── parse ──────────────────────────────────────────

    def parse_shipment(self, raw: list[dict]) -> list[dict]:
        """解析 shipment → 主表 + lead_time 子数据。"""
        result: list[dict] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            lt = item.get("lead_time") or {}
            edt = lt.get("estimated_delivery_time") or {}
            buff = lt.get("buffering") or {}
            esl = lt.get("estimated_schedule_limit") or {}
            edf = lt.get("estimated_delivery_final") or {}
            edl = lt.get("estimated_delivery_limit") or {}
            ede = lt.get("estimated_delivery_extended") or {}
            snapshot = item.get("snapshot_packing") or {}
            logistic = item.get("logistic") or {}
            sm = lt.get("shipping_method") or {}
            offset = edt.get("offset") or {}

            base = {
                "seller_id": int(self.shop.shop_id),
                "order_id": item.get("order_id"),
                "snapshot_id": snapshot.get("snapshot_id"),
                "pack_hash": snapshot.get("pack_hash"),
                "last_updated": parse_datetime(item.get("last_updated")),
                "substatus": item.get("substatus"),
                "date_created": parse_datetime(item.get("date_created")),
                "mode": logistic.get("mode"),
                "type": logistic.get("type"),
                "direction": logistic.get("direction"),
                "external_reference": item.get("external_reference"),
                "tracking_number": item.get("tracking_number"),
                "shipping_id": item.get("id"),
                "status": item.get("status"),
                "tracking_method": item.get("tracking_method"),
                "quotation": item.get("quotation"),
                "items_types": join_csv(item.get("items_types")),
                "threshold_cancellation": item.get("threshold_cancellation"),
                "declared_value": item.get("declared_value"),
                "lead_time": {
                    "seller_id": int(self.shop.shop_id),
                    "order_id": item.get("order_id"),
                    "shipping_id": item.get("id"),
                    "buffering_date": parse_datetime(buff.get("date")),
                    "processing_time": parse_datetime(lt.get("processing_time")),
                    "cost": lt.get("cost"),
                    "estimated_schedule_limit": parse_datetime(esl.get("date")),
                    "cost_type": lt.get("cost_type"),
                    "estimated_delivery_final": parse_datetime(edf.get("date")),
                    "list_cost": lt.get("list_cost"),
                    "estimated_delivery_limit": parse_datetime(edl.get("date")),
                    "priority_class_id": (lt.get("priority_class") or {}).get("id"),
                    "delivery_promise": lt.get("delivery_promise"),
                    "shipping_method_name": sm.get("name"),
                    "shipping_method_deliver_to": sm.get("deliver_to"),
                    "shipping_method_id": sm.get("id"),
                    "shipping_method_type": sm.get("type"),
                    "delivery_type": lt.get("delivery_type"),
                    "service_id": lt.get("service_id"),
                    "estimated_delivery_time": parse_datetime(edt.get("date")),
                    "pay_before": parse_datetime(edt.get("pay_before")),
                    "schedule": edt.get("schedule"),
                    "unit": edt.get("unit"),
                    "offset_date": offset.get("date"),
                    "offset_shipping": offset.get("shipping"),
                    "shipping": edt.get("shipping"),
                    "handling": edt.get("handling"),
                    "estimated_delivery_type": edt.get("type"),
                    "time_frame_from": edt.get("time_frame_from"),
                    "time_frame_to": edt.get("time_frame_to"),
                    "option_id": lt.get("option_id"),
                    "estimated_delivery_extended": parse_datetime(ede.get("date")),
                    "currency_id": lt.get("currency_id"),
                },
            }
            result.append(base)
        return result

    # ── store ──────────────────────────────────────────

    async def store(self, shipment_list: list[dict], sla_list: list[dict] | None = None) -> None:
        if not shipment_list:
            return
        seller_id = int(self.shop.shop_id)

        # ID 映射
        order_ids = [s.get("order_id") for s in shipment_list]
        placeholders = ",".join(["%s"] * len(order_ids))
        id_rows = await repository.select(
            f"SELECT id, seller_id, order_id FROM mercado_order WHERE order_id IN ({placeholders}) AND seller_id = {seller_id}",
            order_ids,
        )
        id_map = {(int(r["seller_id"]), str(r["order_id"])): int(r["id"]) for r in id_rows}

        # 主表
        ship_models: list[dict] = []
        lead_models: list[dict] = []
        for s in shipment_list:
            mid = id_map.get((seller_id, str(s.get("order_id"))))
            if mid is None:
                continue
            s["main_id"] = mid
            # lead_time 独立存储
            lt = s.pop("lead_time", {})
            lt["main_id"] = mid
            lead_models.append(lt)
            ship_models.append(s)

        if ship_models:
            await repository.upsert_batch("mercado_order_shipment", ship_models, ["main_id"])
        if lead_models:
            await repository.upsert_batch("mercado_shipment_lead", lead_models, ["main_id"])

        # SLA
        if sla_list:
            sla_models: list[dict] = []
            for item in sla_list:
                mid = id_map.get((seller_id, str(item.get("order_id"))))
                if mid is None:
                    continue
                sla_models.append({
                    "main_id": mid,
                    "sla_expected_date": parse_datetime(item.get("expected_date")),
                    "sla_service": item.get("service"),
                    "sla_last_updated": parse_datetime(item.get("last_updated")),
                    "sla_status": item.get("status"),
                })
            if sla_models:
                await repository.upsert_batch("mercado_shipment_lead", sla_models, ["main_id"])

    # ── sync ───────────────────────────────────────────

    async def sync_by_shipping_ids(self, shipping_tasks: list[tuple[str, str]]) -> int:
        """按 (shipping_id, order_id) 列表并发生拉取 + 存储。"""
        if not shipping_tasks:
            return 0

        async def _fetch_ship(sid, oid):
            try:
                data = await self.shipment(sid)
                if data:
                    data["order_id"] = oid
                    data["seller_id"] = int(self.shop.shop_id)
                return data
            except Exception as e:
                self.logger.warning("Shipment %s 失败: %s", sid, e)
                return None

        async def _fetch_sla(sid, oid):
            try:
                data = await self.shipment_sla(sid)
                if data:
                    data["shipping_id"] = sid
                    data["order_id"] = oid
                    data["seller_id"] = int(self.shop.shop_id)
                return data
            except Exception as e:
                return None

        ship_results = await asyncio.gather(*[_fetch_ship(s, o) for s, o in shipping_tasks], return_exceptions=True)
        sla_results = await asyncio.gather(*[_fetch_sla(s, o) for s, o in shipping_tasks], return_exceptions=True)

        valid_ships = [r for r in ship_results if isinstance(r, dict) and r]
        valid_slas = [r for r in sla_results if isinstance(r, dict) and r]

        parsed = self.parse_shipment(valid_ships) if valid_ships else []
        await self.store(parsed, valid_slas)
        return len(valid_ships)
