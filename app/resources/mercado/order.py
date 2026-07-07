"""
Mercado 订单资源: OrdersSearch / OrderSearchById / OrderDiscounts 请求/解析/存储/同步。
"""

from app.db.manager import DBManager
from app.http.client import HttpClient
from app.platform.MercadoShop import MercadoShop


class Order:
    """订单资源。"""

    def __init__(self, shop: MercadoShop, qpm: int | None = None) -> None:
        self.shop = shop
        self.client = HttpClient()

    # ── parse ──────────────────────────────────────────

    def parse(self, data: dict):

        order_list = (data.get("results") or []) or [data]
        order_list = []
        items_list = []
        payment_list = []

        for item in order_list:
            cancel_detail = item.get("cancel_detail") or {}
            context = item.get("context") or {}
            coupon = item.get("coupon") or {}
            order_request = item.get("order_request") or {}
            static_tags = item.get("static_tags") or None
            taxes = item.get("taxes") or {}
            feedback = item.get("feedback") or {}
            order_items = item.get("order_items") or []
            payments = item.get("payments") or []
            date_created = item.get("date_created")
            date_closed = item.get("date_closed")
            expiration_date = item.get("expiration_date")
            last_updated = item.get("last_updated")
            manufacturing_ending_date = item.get("manufacturing_ending_date")
            date_last_updated = item.get("date_last_updated")
            cancel_date = cancel_detail.get("date")
            pack_id = item.get("pack_id")

            order_id = str(item.get("id"))

            order_info = {
                "order_id": order_id,
                "status": item.get("status"),
                "date_created": date_created[:19] if date_created else None,
                "date_closed": date_closed[:19] if date_closed else None,
                "expiration_date": expiration_date[:19] if expiration_date else None,
                "fulfilled": item.get("fulfilled"),
                "shipping_id": (item.get("shipping") or {}).get("id"),
                "last_updated": last_updated[:19] if last_updated else None,
                "pack_id": str(pack_id) if pack_id else None,
                "buyer_id": (item.get("buyer") or {}).get("id"),
                "seller_id": (item.get("seller") or {}).get("id"),
                "total_amount": item.get("total_amount"),
                "paid_amount": item.get("paid_amount"),
                "currency_id": item.get("currency_id"),
                "status_detail": item.get("status_detail"),
                "buying_mode": item.get("buying_mode"),
                "shipping_cost": item.get("shipping_cost"),
                "manufacturing_ending_date": manufacturing_ending_date[:19] if manufacturing_ending_date else None,
                "date_last_updated": date_last_updated[:19] if date_last_updated else None,
                "comment": item.get("comment"),
                "cancel_group": cancel_detail.get("group"),
                "cancel_code": cancel_detail.get("code"),
                "cancel_description": cancel_detail.get("description"),
                "cancel_requested_by": cancel_detail.get("requested_by"),
                "cancel_date": cancel_date[:19] if cancel_date else None,
                "cancel_application_id": cancel_detail.get("application_id"),
                "feedback_seller_id": (feedback.get("seller") or {}).get("id"),
                "feedback_buyer_id": (feedback.get("buyer") or {}).get("id"),
                "tags": ",".join(item.get("tags")) if item.get("tags") else None,
                "mediations_id": ",".join([str(item.get("id")) for item in item.get("mediations")]) if item.get("mediations") else None,
                "channel": context.get("channel"),
                "site": context.get("site"),
                "flows": ",".join(context.get("flows") or []) if context.get("flows") else None,
                "coupon_amount": coupon.get("amount"),
                "coupon_id": coupon.get("id"),
                "order_request_change": order_request.get("change"),
                "order_request_return": order_request.get("return"),
                "static_tags": ",".join(static_tags) if static_tags else None,
                "taxes_amount": taxes.get("amount"),
                "taxes_currency_id": taxes.get("currency_id"),
                "taxes_id": taxes.get("id"),
            }
            order_list.append(order_info)

            for order_item in order_items:
                item = order_item.get("item") or {}
                item_info = {
                    "order_id": order_id,
                    "item_id": item.get("id"),
                    "title": item.get("title"),
                    "category_id": item.get("category_id"),
                    "variation_id": item.get("variation_id"),
                    "seller_sku": item.get("seller_sku"),
                    "quantity": order_item.get("quantity"),
                    "unit_price": order_item.get("unit_price"),
                    "gross_price": order_item.get("gross_price"),
                    "currency_id": order_item.get("currency_id"),
                    "sale_fee": order_item.get("sale_fee"),
                    "listing_type_id": order_item.get("listing_type_id"),
                    "element_id": order_item.get("element_id"),
                    "stock_node_id": (order_item.get("stock") or {}).get("node_id"),
                }
                items_list.append(item_info)

            for payment in payments:
                date_approved = payment.get("date_approved")
                date_last_modified = payment.get("date_last_modified")
                date_created = payment.get("date_created")
                payment_info = {
                    "payment_id": payment.get("id"),
                    "order_id": payment.get("order_id"),
                    "payer_id": payment.get("payer_id"),
                    "site_id": payment.get("site_id"),
                    "currency_id": payment.get("currency_id"),
                    "status": payment.get("status"),
                    "reason": payment.get("reason"),
                    "status_detail": payment.get("status_detail"),
                    "total_paid_amount": payment.get("total_paid_amount"),
                    "transaction_amount": payment.get("transaction_amount"),
                    "transaction_amount_refunded": payment.get("transaction_amount_refunded"),
                    "date_approved": date_approved[:19] if date_approved else None,
                    "collector_id": (payment.get("collector") or {}).get("id"),
                    "taxes_amount": payment.get("taxes_amount"),
                    "date_last_modified": date_last_modified[:19] if date_last_modified else None,
                    "coupon_amount": payment.get("coupon_amount"),
                    "shipping_cost": payment.get("shipping_cost"),
                    "date_created": date_created[:19] if date_created else None,
                    "payment_method_id": payment.get("payment_method_id"),
                    "payment_type": payment.get("payment_type"),
                    "status_code": payment.get("status_code"),
                    "operation_type": payment.get("operation_type"),
                    "coupon_id": payment.get("coupon_id"),
                    "installments": payment.get("installments"),
                    "authorization_code": payment.get("authorization_code"),
                    "installment_amount": payment.get("installment_amount"),
                    "activation_uri": payment.get("activation_uri"),
                    "overpaid_amount": payment.get("overpaid_amount"),
                    "card_id": payment.get("card_id"),
                    "issuer_id": payment.get("issuer_id"),
                    "deferred_period": payment.get("deferred_period"),
                    "transaction_order_id": payment.get("transaction_order_id"),
                    "transaction_id": (payment.get("atm_transfer_reference") or {}).get("transaction_id"),
                    "company_id": (payment.get("atm_transfer_reference") or {}).get("company_id"),
                }
                payment_list.append(payment_info)

        return {
            "orders": order_list,
            "items": items_list,
            "payments": payment_list,
        }

    # ── store ──────────────────────────────────────────

    async def store(self, data: dict):
        if not data:
            return 0
        seller_id = int(self.shop.seller_id)

        orders = data.get("orders") or []
        items = data.get("items") or []
        payments = data.get("payments") or []

        await DBManager.upsert("mercado_order", orders, ["seller_id", "order_id"])
        orderids = [item["order_id"] for item in orders]
        placeholders = ",".join(["%s"] * len(orderids))
        id_map = {
            item["order_id"]: item["id"]
            for item in await DBManager.select(
                f"SELECT id,order_id FROM mercado_order WHERE order_id IN ({placeholders}) and seller_id = {seller_id}"
            )
        }

        for item in items:
            item["main_id"] = id_map.get(item["order_id"])
        for item in payments:
            item["main_id"] = id_map.get(item["order_id"])
        await DBManager.upsert("mercado_order_item", items, ["main_id", "item_id"])
        await DBManager.upsert(
            "mercado_order_payment", payments, ["main_id", "payment_id"]
        )

    # ── sync ───────────────────────────────────────────

    async def sync(self):
        pass
