"""
Mercado 订单资源:请求/解析/存储/同步。
"""

import aiohttp
import asyncio
from app.db.manager import DBManager
from datetime import datetime, timedelta
from app.platform.MercadoShop import MercadoShop
from typing import Dict, List
from app.core.converters import _trim, _json, _str


class Order:
    """订单资源。"""

    def __init__(self, shop: MercadoShop):
        self.shop = shop

    @staticmethod
    def _build_params_(search: Dict) -> List:

        datatype = search.get("datatype")
        at = search.get("at")
        to = search.get("to")

        params = {k: v for k, v in search.items() if k not in ("at", "to", "datatype")}

        if datatype is not None:

            params_list = []

            date_fields = {
                0: ("order.date_last_updated.from", "order.date_last_updated.to"),
                1: ("order.date_created.from", "order.date_created.to"),
                2: ("order.date_closed.from", "order.date_closed.to"),
            }

            if datatype not in date_fields:
                raise ValueError(f"不支持的 datatype: {datatype}")

            gte_key, lte_key = date_fields[datatype]

            if at and to:
                current_at = at
                while current_at < to:
                    current_to = current_at + timedelta(days=1)
                    if current_to > to:
                        current_to = to
                    params[gte_key] = current_at.strftime("%Y-%m-%d")
                    params[lte_key] = current_to.strftime("%Y-%m-%d")
                    params_list.append(params.copy())
                    current_at += timedelta(days=1)

                return params_list
            else:
                raise ValueError("at 和 to 必须同时提供")
        else:
            return [params]


    def parse_order(self, results: Dict):

        order_list = results.get("results") or [results]

        order_rows = []
        item_rows = []
        payment_rows = []

        for item in order_list:
            order_items                     = item.get("order_items") or []
            payments                        = item.get("payments") or []

            shipping                        = item.get("shipping") or {}
            feedback                        = item.get("feedback") or {}
            context                         = item.get("context") or {}
            seller                          = item.get("seller") or {}
            buyer                           = item.get("buyer") or {}
            taxes                           = item.get("taxes") or {}
            cancel_detail                   = item.get("cancel_detail") or {}
            coupon                          = item.get("coupon") or {}
            order_request                   = item.get("order_request") or {}

            order_id = _str(item.get("id"))

            order_row = {
                "order_id":                     order_id,
                "status":                       item.get("status"),
                "date_created":                 _trim(item.get("date_created")),
                "date_closed":                  _trim(item.get("date_closed")),
                "expiration_date":              _trim(item.get("expiration_date")),
                "fulfilled":                    item.get("fulfilled"),
                "shipping_id":                  shipping.get("id"),
                "last_updated":                 _trim(item.get("last_updated")),
                "pack_id":                      _str(item.get("pack_id")),
                "buyer_id":                     buyer.get("id"),
                "seller_id":                    seller.get("id"),
                "total_amount":                 item.get("total_amount"),
                "paid_amount":                  item.get("paid_amount"),
                "currency_id":                  item.get("currency_id"),
                "status_detail":                item.get("status_detail"),
                "buying_mode":                  item.get("buying_mode"),
                "shipping_cost":                item.get("shipping_cost"),
                "manufacturing_ending_date":    _trim(item.get("manufacturing_ending_date")),
                "date_last_updated":            _trim(item.get("date_last_updated")),
                "comment":                      item.get("comment"),
                "cancel_group":                 cancel_detail.get("group"),
                "cancel_code":                  cancel_detail.get("code"),
                "cancel_description":           cancel_detail.get("description"),
                "cancel_requested_by":          cancel_detail.get("requested_by"),
                "cancel_date":                  _trim(cancel_detail.get("data")),
                "cancel_application_id":        cancel_detail.get("application_id"),
                "feedback_seller_id":           (feedback.get("seller") or {}).get("id"),
                "feedback_buyer_id":            (feedback.get("buyer") or {}).get("id"),
                "tags":                         _json(item.get("tags")),
                "mediations":                   _json(item.get("mediations")),
                "channel":                      context.get("channel"),
                "site":                         context.get("site"),
                "flows":                        _json(context.get("flows")),
                "coupon_amount":                coupon.get("amount"),
                "coupon_id":                    coupon.get("id"),
                "order_request_change":         order_request.get("change"),
                "order_request_return":         order_request.get("return"),
                "static_tags":                  _json(item.get("static_tags")),
                "taxes_amount":                 taxes.get("amount"),
                "taxes_currency_id":            taxes.get("currency_id"),
                "taxes_id":                     taxes.get("id"),
            }
            order_rows.append(order_row)

            for order_item in order_items:
                item = order_item.get("item") or {}
                stock = order_item.get("stock") or {}
                item_row = {
                    "order_id":                 order_id,
                    "item_id":                  item.get("id"),
                    "title":                    item.get("title"),
                    "category_id":              item.get("category_id"),
                    "variation_id":             item.get("variation_id"),
                    "seller_custom_field":      item.get("seller_custom_field"),
                    "variation_attributes":     _json(item.get("variation_attributes")),
                    "warranty":                 item.get("warranty"),
                    "condition":                item.get("condition"),
                    "seller_sku":               item.get("seller_sku"),
                    "global_price":             item.get("global_price"),
                    "net_weight":               item.get("net_weight"),
                    "user_product_id":          item.get("user_product_id"),
                    "release_date":             _trim(item.get("release_date")),
                    "attributes":               _json(item.get("attributes")),
                    "quantity":                 order_item.get("quantity"),
                    "requested_quantity":       order_item.get("requested_quantity"),
                    "picked_quantity":          order_item.get("picked_quantity"),
                    "unit_price":               order_item.get("unit_price"),
                    "currency_id":              order_item.get("currency_id"),
                    "manufacturing_days":       order_item.get("manufacturing_days"),
                    "sale_fee":                 order_item.get("sale_fee"),
                    "listing_type_id":          order_item.get("listing_type_id"),
                    "base_exchange_rate":       order_item.get("base_exchange_rate"),
                    "base_currency_id":         order_item.get("base_currency_id"),
                    "element_id":               order_item.get("element_id"),
                    "discounts":                order_item.get("discounts"),
                    "bundle":                   order_item.get("bundle"),
                    "compat_id":                order_item.get("compat_id"),
                    "node_id":                  stock.get("node_id"),
                    "store_id":                 stock.get("store_id"),
                    "kit_instance_id":          order_item.get("kit_instance_id"),
                    "gross_price":              order_item.get("gross_price")
                }
                item_rows.append(item_row)

            for payment in payments:
                collector = payment.get("collector") or {}
                atm_transfer_reference = payment.get("atm_transfer_reference") or {}
                payment_row = {
                    "payment_id":                               payment.get("id"),
                    "order_id":                                 payment.get("order_id"),
                    "payer_id":                                 payment.get("payer_id"),
                    "site_id":                                  payment.get("site_id"),
                    "currency_id":                              payment.get("currency_id"),
                    "status":                                   payment.get("status"),
                    "reason":                                   payment.get("reason"),
                    "status_detail":                            payment.get("status_detail"),
                    "total_paid_amount":                        payment.get("total_paid_amount"),
                    "transaction_amount":                       payment.get("transaction_amount"),
                    "transaction_amount_refunded":              payment.get("transaction_amount_refunded"),
                    "date_approved":                            _trim(payment.get("date_approved")),
                    "collector_id":                             collector.get("id"),
                    "taxes_amount":                             payment.get("taxes_amount"),
                    "date_last_modified":                       _trim(payment.get("date_last_modified")),
                    "coupon_amount":                            payment.get("coupon_amount"),
                    "shipping_cost":                            payment.get("shipping_cost"),
                    "date_created":                             _trim(payment.get("date_created")),
                    "payment_method_id":                        payment.get("payment_method_id"),
                    "payment_type":                             payment.get("payment_type"),
                    "status_code":                              payment.get("status_code"),
                    "operation_type":                           payment.get("operation_type"),
                    "coupon_id":                                payment.get("coupon_id"),
                    "installments":                             payment.get("installments"),
                    "authorization_code":                       payment.get("authorization_code"),
                    "installment_amount":                       payment.get("installment_amount"),
                    "activation_uri":                           payment.get("activation_uri"),
                    "overpaid_amount":                          payment.get("overpaid_amount"),
                    "card_id":                                  payment.get("card_id"),
                    "issuer_id":                                payment.get("issuer_id"),
                    "deferred_period":                          payment.get("deferred_period"),
                    "transaction_order_id":                     payment.get("transaction_order_id"),
                    "transaction_id":                           atm_transfer_reference.get("transaction_id"),
                    "company_id":                               atm_transfer_reference.get("company_id"),
                }
                payment_rows.append(payment_row)

        return {
            "orders": order_list,
            "items": item_rows,
            "payments": payment_rows,
        }


    async def save_order(self, data: Dict):
        pass


    async def search_order_by_id(self, session: aiohttp.ClientSession, order_id: str):

        resp = await self.shop.request(
            session=session,
            method="GET",
            url=f"/orders/{order_id}",
            headers={
                "Content-Type": "application/json",
            }
        )
        return resp


    async def search_order(self, session: aiohttp.ClientSession, search: Dict):

        datatype = search.get("datatype")
        at = search.get("at")
        to = search.get("to")

        params = {k: v for k, v in search.items() if k not in ("at", "to", "datatype")}


        date_fields = {
            0: ("order.date_last_updated.from", "order.date_last_updated.to"),
            1: ("order.date_created.from", "order.date_created.to"),
            2: ("order.date_closed.from", "order.date_closed.to"),
        }

        if datatype not in date_fields:
            raise ValueError(f"不支持的 datatype: {datatype}")

        gte_key, lte_key = date_fields[datatype]

        if at and to:
            params[gte_key] = at
            params[lte_key] = to

        resp = await self.shop.request(
            session=session,
            method="GET",
            url="/orders",
            params=params,
            headers={
                "Content-Type": "application/json",
            }
        )
        return resp


    async def sync_order(self, session: aiohttp.ClientSession, search: Dict):

        params_list = Order._build_params_(search)


        for params in params_list:

            limit = 50
            offset = 0
            total = None

            while total is None or offset < total:

                resp = await self.shop.request(
                    session=session,
                    method="GET",
                    url="/orders",
                    params={**params, "limit": limit, "offset": offset},
                    headers={
                        "Content-Type": "application/json",
                    }
                )

                if total is None:
                    total = (resp.get("paging") or {}).get("total",0) or 0
                    if total == 0:
                        break

                if not resp.get("results"):
                    break

                parsed = self.parse_order(resp)
                await self.save_order(parsed)
