"""Mercado Libre 平台 pydantic 数据模型。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# ===================== Product =====================

class MercadoProduct(BaseModel):
    """表 mercado_product"""
    seller_id: int
    item_id: str
    variation_id: str = ""
    site_id: Optional[str] = None
    title: Optional[str] = None
    family_id: Optional[str] = None
    family_name: Optional[str] = None
    category_id: Optional[str] = None
    user_product_id: Optional[str] = None
    official_store_id: Optional[int] = None
    price: Optional[Decimal] = None
    base_price: Optional[Decimal] = None
    original_price: Optional[Decimal] = None
    inventory_id: Optional[str] = None
    currency_id: Optional[str] = None
    initial_quantity: Optional[int] = None
    available_quantity: Optional[int] = None
    sold_quantity: Optional[int] = None
    buying_mode: Optional[str] = None
    listing_type_id: Optional[str] = None
    start_time: Optional[str] = None
    stop_time: Optional[str] = None
    end_time: Optional[str] = None
    expiration_time: Optional[str] = None
    condition: Optional[str] = Field(default=None, alias="`condition`")
    permalink: Optional[str] = None
    thumbnail: Optional[str] = None
    video_id: Optional[str] = None
    descriptions: Optional[str] = None
    accepts_mercadopago: Optional[bool] = None
    status: Optional[str] = None
    sub_status: Optional[str] = None
    tags: Optional[str] = None
    warranty: Optional[str] = None
    catalog_product_id: Optional[str] = None
    domain_id: Optional[str] = None
    seller_custom_field: Optional[str] = None
    parent_item_id: Optional[str] = None
    differential_pricing: Optional[str] = None
    automatic_relist: Optional[bool] = None
    health: Optional[str] = None
    catalog_listing: Optional[str] = None
    item_relations: Optional[str] = None
    channels: Optional[str] = None
    date_created: Optional[str] = None
    last_updated: Optional[str] = None


class MercadoProductImage(BaseModel):
    """表 mercado_product_image"""
    main_id: int
    image_id: Optional[str] = None
    item_id: Optional[str] = None
    variation_id: str = ""
    url: Optional[str] = None


class MercadoProductAttribute(BaseModel):
    """表 mercado_product_attribute"""
    main_id: int
    attribute_id: Optional[str] = None
    attribute_name: Optional[str] = None
    value_id: Optional[str] = None
    value_name: Optional[str] = None
    seller_id: Optional[int] = None
    item_id: Optional[str] = None
    variation_id: Optional[str] = None


# ===================== Order =====================

class MercadoOrder(BaseModel):
    """表 mercado_order"""
    order_id: str
    seller_id: int
    status: Optional[str] = None
    date_created: Optional[str] = None
    date_closed: Optional[str] = None
    expiration_date: Optional[str] = None
    date_last_updated: Optional[str] = None
    manufacturing_ending_date: Optional[str] = None
    buying_mode: Optional[str] = None
    shipping_cost: Optional[Decimal] = None
    comment: Optional[str] = None
    cancel_group: Optional[str] = None
    cancel_code: Optional[str] = None
    cancel_description: Optional[str] = None
    cancel_requested_by: Optional[str] = None
    cancel_date: Optional[str] = None
    cancel_application_id: Optional[str] = None
    fulfilled: Optional[bool] = None
    shipping_id: Optional[str] = None
    last_updated: Optional[str] = None
    pack_id: Optional[str] = None
    buyer_id: Optional[int] = None
    total_amount: Optional[Decimal] = None
    paid_amount: Optional[Decimal] = None
    currency_id: Optional[str] = None
    status_detail: Optional[str] = None
    feedback_seller_id: Optional[str] = None
    feedback_buyer_id: Optional[str] = None
    tags: Optional[str] = None
    mediations_id: Optional[str] = None
    channel: Optional[str] = None
    site: Optional[str] = None
    flows: Optional[str] = None
    coupon_amount: Optional[Decimal] = None
    coupon_id: Optional[str] = None
    order_request_change: Optional[str] = None
    order_request_return: Optional[str] = None
    static_tags: Optional[str] = None
    taxes_amount: Optional[Decimal] = None
    taxes_currency_id: Optional[str] = None
    taxes_id: Optional[str] = None


class MercadoOrderItem(BaseModel):
    """表 mercado_order_item"""
    main_id: int
    item_id: Optional[str] = None
    title: Optional[str] = None
    category_id: Optional[str] = None
    variation_id: Optional[str] = None
    seller_sku: Optional[str] = None
    quantity: Optional[int] = None
    unit_price: Optional[Decimal] = None
    gross_price: Optional[Decimal] = None
    currency_id: Optional[str] = None
    sale_fee: Optional[Decimal] = None
    listing_type_id: Optional[str] = None
    element_id: Optional[str] = None
    stock_node_id: Optional[str] = None
    order_id: Optional[str] = None


class MercadoOrderPayment(BaseModel):
    """表 mercado_order_payment"""
    main_id: int
    payment_id: Optional[str] = None
    order_id: Optional[str] = None
    payer_id: Optional[str] = None
    site_id: Optional[str] = None
    currency_id: Optional[str] = None
    status: Optional[str] = None
    reason: Optional[str] = None
    status_detail: Optional[str] = None
    total_paid_amount: Optional[Decimal] = None
    transaction_amount: Optional[Decimal] = None
    transaction_amount_refunded: Optional[Decimal] = None
    date_approved: Optional[str] = None
    collector_id: Optional[str] = None
    taxes_amount: Optional[Decimal] = None
    date_last_modified: Optional[str] = None
    coupon_amount: Optional[Decimal] = None
    shipping_cost: Optional[Decimal] = None
    date_created: Optional[str] = None
    payment_method_id: Optional[str] = None
    payment_type: Optional[str] = None
    status_code: Optional[str] = None
    operation_type: Optional[str] = None
    coupon_id: Optional[str] = None
    installments: Optional[int] = None
    authorization_code: Optional[str] = None
    installment_amount: Optional[Decimal] = None
    activation_uri: Optional[str] = None
    overpaid_amount: Optional[Decimal] = None
    card_id: Optional[str] = None
    issuer_id: Optional[str] = None
    deferred_period: Optional[str] = None
    transaction_order_id: Optional[str] = None
    transaction_id: Optional[str] = None
    company_id: Optional[str] = None


# ===================== Shipment =====================

class MercadoOrderShipment(BaseModel):
    """表 mercado_order_shipment"""
    main_id: int
    snapshot_id: Optional[str] = None
    pack_hash: Optional[int] = None
    last_updated: Optional[str] = None
    substatus: Optional[str] = None
    date_created: Optional[str] = None
    mode: Optional[str] = None
    type: Optional[str] = None
    direction: Optional[str] = None
    external_reference: Optional[str] = None
    tracking_number: Optional[str] = None
    shipping_id: Optional[str] = None
    status: Optional[str] = None
    tracking_method: Optional[str] = None
    quotation: Optional[str] = None
    items_types: Optional[str] = None
    threshold_cancellation: Optional[str] = None
    declared_value: Optional[str] = None
    order_id: Optional[str] = None


class MercadoShipmentLead(BaseModel):
    """表 mercado_shipment_lead"""
    main_id: int
    buffering_date: Optional[str] = None
    processing_time: Optional[str] = None
    cost: Optional[Decimal] = None
    estimated_schedule_limit: Optional[str] = None
    cost_type: Optional[str] = None
    estimated_delivery_final: Optional[str] = None
    list_cost: Optional[Decimal] = None
    estimated_delivery_limit: Optional[str] = None
    priority_class_id: Optional[str] = None
    delivery_promise: Optional[str] = None
    shipping_method_name: Optional[str] = None
    shipping_method_deliver_to: Optional[str] = None
    shipping_method_id: Optional[str] = None
    shipping_method_type: Optional[str] = None
    delivery_type: Optional[str] = None
    service_id: Optional[str] = None
    estimated_delivery_time: Optional[str] = None
    pay_before: Optional[str] = None
    schedule: Optional[str] = None
    unit: Optional[str] = None
    offset_date: Optional[str] = None
    offset_shipping: Optional[str] = None
    shipping: Optional[str] = None
    handling: Optional[str] = None
    estimated_delivery_type: Optional[str] = None
    time_frame_from: Optional[str] = None
    time_frame_to: Optional[str] = None
    option_id: Optional[str] = None
    estimated_delivery_extended: Optional[str] = None
    currency_id: Optional[str] = None
    sla_expected_date: Optional[str] = None
    sla_service: Optional[str] = None
    sla_last_updated: Optional[str] = None
    sla_status: Optional[str] = None


# ===================== Stock =====================

class MercadoProductStock(BaseModel):
    """表 mercado_product_stock"""
    seller_id: int
    user_product_id: str
    upsert_date: Optional[str] = None
    selling_address: Optional[int] = 0
    meli_facility: Optional[int] = 0
    seller_warehouse: Optional[int] = 0


# ===================== Review =====================

class MercadoProductRate(BaseModel):
    """表 mercado_product_rate"""
    main_id: int
    seller_id: Optional[int] = None
    item_id: Optional[str] = None
    rating_average: Optional[float] = None
    stars: Optional[int] = None
    one_star: Optional[str] = "0"
    two_star: Optional[str] = "0"
    three_star: Optional[str] = "0"
    four_star: Optional[str] = "0"
    five_star: Optional[str] = "0"
