"""Mercado Libre 平台专属解析辅助函数。

负责账单分组 (ML/MP/FLEX/FULL) 的专用解析, 以及 Mercado 特有的
Nested dict 提取 / item attributes 拼装 / shipment lead_time 提取等。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from app.core.converters import (
    as_list,
    parse_datetime,
    safe_get,
    to_decimal,
    to_int,
    to_str,
    join_csv,
)


def extract_billing_group(group: str) -> str | None:
    """将 group 简码映射为表后缀。"""
    mapping = {"ML": "ml", "MP": "mp", "FLEX": "flex", "FULL": "full"}
    return mapping.get(group.upper())


def parse_ml_billing_items(items: list[dict]) -> list[dict]:
    """解析 ML (marketplace) 账单明细 → 展平字典列表。"""
    result: list[dict] = []
    for item in items:
        charge = item.get("charge_info") or {}
        discount = item.get("discount_info") or {}
        shipping = item.get("shipping_info") or {}
        document = item.get("document_info") or {}
        marketplace = item.get("marketplace_info") or {}
        currency = item.get("currency_info") or {}
        sales = as_list(item.get("sales_info") or [])
        items_info = as_list(item.get("items_info") or [])
        sales_d = sales[0] if sales else {}
        items_d = items_info[0] if items_info else {}

        result.append({
            "currency_id": currency.get("currency_id"),
            "marketplace": marketplace.get("marketplace"),
            "document_id": document.get("document_id"),
            "shipping_id": shipping.get("shipping_id"),
            "pack_id": shipping.get("pack_id"),
            "receiver_shipping_cost": shipping.get("receiver_shipping_cost"),
            "charge_amount_without_discount": discount.get("charge_amount_without_discount"),
            "discount_amount": discount.get("discount_amount"),
            "discount_reason": discount.get("discount_reason"),
            "rebate": discount.get("rebate"),
            "legal_document_number": charge.get("legal_document_number"),
            "legal_document_status": charge.get("legal_document_status"),
            "legal_document_status_description": charge.get("legal_document_status_description"),
            "creation_date_time": charge.get("creation_date_time"),
            "detail_id": charge.get("detail_id"),
            "transaction_detail": charge.get("transaction_detail"),
            "debited_from_operation": charge.get("debited_from_operation"),
            "debited_from_operation_description": charge.get("debited_from_operation_description"),
            "status": charge.get("status"),
            "status_description": charge.get("status_description"),
            "charge_bonified_id": charge.get("charge_bonified_id"),
            "detail_amount": charge.get("detail_amount"),
            "detail_type": charge.get("detail_type"),
            "detail_sub_type": charge.get("detail_sub_type"),
            "order_id": sales_d.get("order_id"),
            "operation_id": sales_d.get("operation_id"),
            "sale_date_time": sales_d.get("sale_date_time"),
            "sales_channel": sales_d.get("sales_channel"),
            "payer_nickname": sales_d.get("payer_nickname"),
            "state_name": sales_d.get("state_name"),
            "transaction_amount": sales_d.get("transaction_amount"),
            "wholesale_price": sales_d.get("wholesale_price"),
            "item_id": items_d.get("item_id"),
            "item_title": items_d.get("item_title"),
            "item_type": items_d.get("item_type"),
            "item_category": items_d.get("item_category"),
            "inventory_id": items_d.get("inventory_id"),
            "item_amount": items_d.get("item_amount"),
            "item_price": items_d.get("item_price"),
        })
    return result


def parse_mp_billing_items(items: list[dict]) -> list[dict]:
    """解析 MP (mercadopago) 账单明细。"""
    result: list[dict] = []
    for item in items:
        charge = item.get("charge_info") or {}
        operation = item.get("operation_info") or {}
        perception = item.get("perception_info") or {}
        document = item.get("document_info") or {}
        marketplace = item.get("marketplace_info") or {}
        currency = item.get("currency_info") or {}

        result.append({
            "currency_id": currency.get("currency_id"),
            "marketplace": marketplace.get("marketplace"),
            "document_id": document.get("document_id"),
            "legal_document_number": charge.get("legal_document_number"),
            "legal_document_status": charge.get("legal_document_status"),
            "legal_document_status_description": charge.get("legal_document_status_description"),
            "detail_id": charge.get("detail_id"),
            "movement_id": charge.get("movement_id"),
            "transaction_detail": charge.get("transaction_detail"),
            "debited_from_operation": charge.get("debited_from_operation"),
            "debited_from_operation_description": charge.get("debited_from_operation_description"),
            "status": charge.get("status"),
            "status_description": charge.get("status_description"),
            "charge_bonified_id": charge.get("charge_bonified_id"),
            "creation_date_time": charge.get("creation_date_time"),
            "detail_amount": charge.get("detail_amount"),
            "detail_type": charge.get("detail_type"),
            "detail_sub_type": charge.get("detail_sub_type"),
            "operation_type": operation.get("operation_type"),
            "operation_type_description": operation.get("operation_type_description"),
            "reference_id": operation.get("reference_id"),
            "sales_channel": operation.get("sales_channel"),
            "store_id": operation.get("store_id"),
            "store_name": operation.get("store_name"),
            "external_reference": operation.get("external_reference"),
            "payer_nickname": operation.get("payer_nickname"),
            "transaction_amount": operation.get("transaction_amount"),
            "aliquot": perception.get("aliquot"),
            "taxable_amount": perception.get("taxable_amount"),
        })
    return result


def parse_flex_billing_items(items: list[dict]) -> list[dict]:
    """解析 FLEX 账单明细。"""
    result: list[dict] = []
    for item in items:
        charge = item.get("charge_info") or {}
        shipping = item.get("shipping_info") or {}
        document = item.get("document_info") or {}
        order = shipping.get("order") or {}

        result.append({
            "document_id": document.get("document_id"),
            "legal_document_number": charge.get("legal_document_number"),
            "legal_document_status": charge.get("legal_document_status"),
            "legal_document_status_description": charge.get("legal_document_status_description"),
            "creation_date_time": charge.get("creation_date_time"),
            "detail_id": charge.get("detail_id"),
            "detail_associated_id": charge.get("detail_associated_id"),
            "detail_amount": charge.get("detail_amount"),
            "transaction_detail": charge.get("transaction_detail"),
            "detail_type": charge.get("detail_type"),
            "detail_sub_type": charge.get("detail_sub_type"),
            "concept_type": charge.get("concept_type"),
            "shipping_id": shipping.get("shipping_id"),
            "receiver_nickname": shipping.get("receiver_nickname"),
            "pack_id": shipping.get("pack_id"),
            "receiver_shipping_cost": shipping.get("receiver_shipping_cost"),
            "order_id": order.get("order_id"),
            "date_created": order.get("date_created"),
            "total_amount": order.get("total_amount"),
            "payment_id": order.get("payment_id"),
            "buyer_nickname": order.get("buyer_nickname"),
        })
    return result


def parse_full_billing_items(items: list[dict]) -> list[dict]:
    """解析 FULL (fulfillment) 账单明细。"""
    result: list[dict] = []
    for item in items:
        charge = item.get("charge_info") or {}
        fulfillment = item.get("fulfillment_info") or {}
        document = item.get("document_info") or {}

        result.append({
            "document_id": document.get("document_id"),
            "legal_document_number": charge.get("legal_document_number"),
            "legal_document_status": charge.get("legal_document_status"),
            "legal_document_status_description": charge.get("legal_document_status_description"),
            "creation_date_time": charge.get("creation_date_time"),
            "detail_id": charge.get("detail_id"),
            "detail_amount": charge.get("detail_amount"),
            "transaction_detail": charge.get("transaction_detail"),
            "charge_bonified_id": charge.get("charge_bonified_id"),
            "detail_type": charge.get("detail_type"),
            "detail_sub_type": charge.get("detail_sub_type"),
            "concept_type": charge.get("concept_type"),
            "payment_id": fulfillment.get("payment_id"),
            "type": fulfillment.get("type"),
            "amount_per_unit": fulfillment.get("amount_per_unit"),
            "amount": fulfillment.get("amount"),
            "sku": fulfillment.get("sku"),
            "ean": fulfillment.get("ean"),
            "item_id": fulfillment.get("item_id"),
            "item_title": fulfillment.get("item_title"),
            "variation": fulfillment.get("variation"),
            "quantity": fulfillment.get("quantity"),
            "volume_type": fulfillment.get("volume_type"),
            "inventory_id": fulfillment.get("inventory_id"),
            "warehouse_id": fulfillment.get("warehouse_id"),
            "source_id": fulfillment.get("source_id"),
            "item_quantity": fulfillment.get("item_quantity"),
        })
    return result


BILLING_PARSER = {
    "ML": parse_ml_billing_items,
    "MP": parse_mp_billing_items,
    "FLEX": parse_flex_billing_items,
    "FULL": parse_full_billing_items,
}
