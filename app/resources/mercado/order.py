"""
Mercado order,shipment,pack,discount资源:请求/解析/存储/同步。
"""
import asyncio
from app.db.manager import DBManager
from datetime import timedelta
from app.platform.MercadoShop import MercadoShop
from typing import Dict, List
from app.core.converters import _trim, _json, _str, _lstr


class Order:
    """order资源。shipment资源"""

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
                    params[gte_key] = current_at.isoformat()
                    params[lte_key] = current_to.isoformat()
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
                "mediations":                   _json(item.get("mediations")),#mediations_id
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
                    "requested_quantity":       _json(order_item.get("requested_quantity")),
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
                    "stock_node_id":            stock.get("node_id"),
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
                    "order_id":                                 str(payment.get("order_id")),
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
                    "available_actions":                        _json(payment.get("available_actions")),
                    "marketplace_fee":                          payment.get("marketplace_fee"),
                    "reference_id":                             payment.get("reference_id"),
                    "visible_by":                               payment.get("visible_by"),
                }
                payment_rows.append(payment_row)

        return {
            "order_rows": order_rows,
            "item_rows": item_rows,
            "payment_rows": payment_rows,
        }


    def parse_shipmentsla(self, data: Dict) -> Dict:

        if not data:
            return {}

        sla =  {
            "sla_status":           data.get("status"),
            "sla_expected_date":    _trim(data.get("expected_date")),
            "sla_service":          data.get("service"),
            "sla_last_updated":     _trim(data.get("last_updated")),
        }

        return sla


    def parse_shipment(self, data: Dict):
        lead_time =             data.get('lead_time') or {}
        snapshot_packing =      data.get("snapshot_packing") or {}
        logistic =              data.get('logistic') or {}
        origin =                data.get("origin") or {}

        shipment = {
            "snapshot_id":                      snapshot_packing.get("snapshot_id"),
            "pack_hash":                        snapshot_packing.get('pack_hash'),
            "last_updated":                     _trim(data.get('last_updated')),
            # "threshold_cancellation":           data.get('threshold_cancellation'),#new
            "substatus":                        data.get('substatus'),
            "date_created":                     _trim(data.get('date_created')),
            "declared_value":                   data.get('declared_value'),
            "mode":                             logistic.get('mode'),
            "type":                             logistic.get('type'),
            "direction":                        logistic.get('direction'),
            "external_reference":               data.get('external_reference'),
            "tracking_number":                  data.get('tracking_number'),
            "shipping_id":                      data.get('id'),
            "status":                           data.get('status'),
            "tracking_method":                  data.get('tracking_method'),
            "quotation":                        data.get('quotation'),
            "items_types":                      _lstr(data.get('items_types')),
            "node_id":                          (origin.get("node") or {}).get("node_id")
        }


        buffering                       = lead_time.get("buffering") or {}
        priority_class                  = lead_time.get("priority_class") or {}
        shipping_method                 = lead_time.get("shipping_method") or {}
        estimated_schedule_limit        = lead_time.get("estimated_schedule_limit") or {}
        estimated_delivery_limit        = lead_time.get("estimated_delivery_limit") or {}
        estimated_delivery_final        = lead_time.get("estimated_delivery_final") or {}
        estimated_delivery_extended     = lead_time.get("estimated_delivery_extended") or {}
        estimated_delivery_time         = lead_time.get("estimated_delivery_time") or {}
        new_lead_time =  {
            "seller_id":                            self.shop.seller_id,
            "shipping_id":                          data.get('id'),
            "buffering_date":                       _trim(buffering.get("date")),
            "processing_time":                      _trim(lead_time.get('processing_time')),
            "cost":                                 lead_time.get('cost'),
            "estimated_schedule_limit":             _trim(estimated_schedule_limit.get('date')),
            "cost_type":                            lead_time.get('cost_type'),
            "estimated_delivery_final":             _trim(estimated_delivery_final.get('date')),
            "list_cost":                            lead_time.get('list_cost'),
            "estimated_delivery_limit":             _trim(estimated_delivery_limit.get('date')),
            "priority_class_id":                    priority_class.get("id"),
            "delivery_promise":                     lead_time.get('delivery_promise'),
            "shipping_method_name":                 shipping_method.get('name'),
            "shipping_method_deliver_to":           shipping_method.get('deliver_to'),
            "shipping_method_id":                   shipping_method.get('id'),
            "shipping_method_type":                 shipping_method.get('type'),
            "delivery_type":                        lead_time.get('delivery_type'),
            "service_id":                           lead_time.get('service_id'),
            "estimated_delivery_time":              _trim(estimated_delivery_time.get('date')),
            "pay_before":                           _trim(estimated_delivery_time.get('pay_before')),
            "schedule":                             estimated_delivery_time.get('schedule'),
            "unit":                                 estimated_delivery_time.get('unit'),
            "offset_date":                          (estimated_delivery_time.get('offset') or {}).get("date"),
            "offset_shipping":                      (estimated_delivery_time.get('offset') or {}).get("shipping"),
            "shipping":                             estimated_delivery_time.get('shipping'),
            "handling":                             estimated_delivery_time.get('handling'),
            "estimated_delivery_type":              estimated_delivery_time.get('type'),
            "time_frame_from":                      (estimated_delivery_time.get('time_frame') or {}).get("from"),
            "time_frame_to":                        (estimated_delivery_time.get('time_frame') or {}).get("to"),
            "option_id":                            lead_time.get('option_id'),
            "estimated_delivery_extended":          _trim(estimated_delivery_extended.get('date')),
            "currency_id":                          lead_time.get('currency_id'),
        }

        return shipment,new_lead_time


    def parse_payment(self, data: Dict):
        """解析 /v1/payments/{id} 响应, 返回 payment 主表行 + charge 明细行列表。"""

        if not data:
            return {}, []

        # ── 子对象解包 ──────────────────────────────────────
        payer                   = data.get("payer") or {}
        payer_identification    = payer.get("identification") or {}
        payer_phone             = payer.get("phone") or {}
        transaction_details     = data.get("transaction_details") or {}
        payment_method          = data.get("payment_method") or {}
        order_info              = data.get("order") or {}
        fee_details             = data.get("fee_details") or []
        point_of_interaction    = data.get("point_of_interaction") or {}
        additional_info         = data.get("additional_info") or {}
        amounts                 = data.get("amounts") or {}
        metadata                = data.get("metadata") or {}
        charges_execution_info  = data.get("charges_execution_info") or {}
        card                    = data.get("card") or {}

        # ── 支付主表行 ──────────────────────────────────────
        payment_row = {
            "payment_id":                   data.get("id"),
            "order_id":                     order_info.get("id"),

            # 状态
            "status":                       data.get("status"),
            "status_detail":                data.get("status_detail"),
            "money_release_status":         data.get("money_release_status"),
            "captured":                     1 if data.get("captured") else 0,

            # 时间
            "date_created":                 _trim(data.get("date_created")),
            "date_approved":                _trim(data.get("date_approved")),
            "date_last_updated":            _trim(data.get("date_last_updated")),
            "money_release_date":           _trim(data.get("money_release_date")),
            "date_of_expiration":           _trim(data.get("date_of_expiration")),

            # 金额
            "currency_id":                  data.get("currency_id"),
            "transaction_amount":           data.get("transaction_amount"),
            "transaction_amount_refunded":  data.get("transaction_amount_refunded"),
            "total_paid_amount":            transaction_details.get("total_paid_amount"),
            "net_received_amount":          transaction_details.get("net_received_amount"),
            "overpaid_amount":              transaction_details.get("overpaid_amount") or 0,
            "installment_amount":           transaction_details.get("installment_amount") or 0,
            "taxes_amount":                 data.get("taxes_amount"),
            "coupon_amount":                data.get("coupon_amount"),
            "shipping_amount":              data.get("shipping_amount"),

            # 分期
            "installments":                 data.get("installments"),

            # 支付方式
            "payment_method_id":            data.get("payment_method_id"),
            "payment_type_id":              data.get("payment_type_id"),
            "operation_type":               data.get("operation_type"),
            "authorization_code":           data.get("authorization_code"),
            "issuer_id":                    data.get("issuer_id"),

            # 关联方
            "collector_id":                 data.get("collector_id"),
            "payer_id":                     payer.get("id"),
            "payer_type":                   payer.get("type"),
            "payer_email":                  payer.get("email"),
            "payer_first_name":             payer.get("first_name"),
            "payer_last_name":              payer.get("last_name"),

            # 其他
            "description":                  data.get("description"),
            "external_reference":           data.get("external_reference"),
            "tags":                         ",".join(data.get("tags") or []),
            "money_release_schema":         data.get("money_release_schema"),
            "call_for_authorize_id":        data.get("call_for_authorize_id"),
            "card_id":                      card.get("id"),
            "financing_group":              data.get("financing_group"),
            "marketplace_owner":            data.get("marketplace_owner"),
            "merchant_account_id":          data.get("merchant_account_id"),
            "deduction_schema":             data.get("deduction_schema"),
            "differential_pricing_id":      data.get("differential_pricing_id"),
            "notification_url":             data.get("notification_url"),
            "sponsor_id":                   data.get("sponsor_id"),
            "store_id":                     data.get("store_id"),
            "pos_id":                       data.get("pos_id"),
            "platform_id":                  data.get("platform_id"),
            "integrator_id":                data.get("integrator_id"),
            "corporation_id":               data.get("corporation_id"),
            "brand_id":                     data.get("brand_id"),
            "statement_descriptor":         data.get("statement_descriptor"),
            "counter_currency":             data.get("counter_currency"),
            "build_version":                data.get("build_version"),
            "binary_mode":                  1 if data.get("binary_mode") else 0,
            "live_mode":                    1 if data.get("live_mode") else 0,
            "processing_mode":              data.get("processing_mode"),

            # JSON 列
            "payer_identification":         _json(payer_identification),
            "payer_phone":                  _json(payer_phone),
            "payment_method":               _json(payment_method),
            "order_info":                   _json(order_info),
            "metadata":                     _json(metadata),
            "transaction_details":          _json(transaction_details),
            "fee_details":                  _json(fee_details),
            "point_of_interaction":         _json(point_of_interaction),
            "additional_info":              _json(additional_info),
            "amounts_collector":            _json(amounts.get("collector")),
            "amounts_payer":                _json(amounts.get("payer")),
            "charges_execution_info":       _json(charges_execution_info),
            "accounts_info":                _json(data.get("accounts_info")),
            "release_info":                 _json(data.get("release_info")),
        }

        # ── 费用明细行 ──────────────────────────────────────
        charge_rows = []
        charges_details = data.get("charges_details") or []
        for charge in charges_details:
            charge_amounts = charge.get("amounts") or {}
            charge_accounts = charge.get("accounts") or {}
            charge_metadata = charge.get("metadata") or {}
            charge_row = {
                "payment_id":           data.get("id"),
                "order_id":             order_info.get("id"),
                "charge_id":            charge.get("id"),
                "charge_name":          charge.get("name"),
                "charge_type":          charge.get("type"),
                "amount_original":      charge_amounts.get("original"),
                "amount_refunded":      charge_amounts.get("refunded") or 0,
                "currency_id":          charge_amounts.get("currency_id"),
                "accounts_from":        charge_accounts.get("from"),
                "accounts_to":          charge_accounts.get("to"),
                "client_id":            charge.get("client_id"),
                "reserve_id":           charge.get("reserve_id"),
                "date_created":         _trim(charge.get("date_created")),
                "last_updated":         _trim(charge.get("last_updated")),
                "metadata":             _json(charge_metadata),
                "refund_charges":       _json(charge.get("refund_charges")),
                "counter_currencies":   _json(charge_amounts.get("counter_currencies")),
            }
            charge_rows.append(charge_row)

        return payment_row, charge_rows


    def parse_discount(self, data: Dict) -> List[Dict]:
        """解析折扣明细 API 响应 (c.json 格式), 返回 (discount_rows)。"""

        if not data:
            return []

        details = data.get("details") or []

        discount_rows = []
        for detail in details:
            discount_type = detail.get("type")

            supplier = detail.get("supplier") or {}
            counter_currency = detail.get("counter_currency") or {}

            items = detail.get("items") or []
            for item in items:
                amounts = item.get("amounts") or {}

                discount_rows.append(
                    {
                        "seller_id":            self.shop.seller_id,
                        "element_id":           item.get("element_id"),
                        "quantity":             item.get("quantity"),
                        "item_id":              item.get("id"),
                        "total":                amounts.get("total"),
                        "seller":               amounts.get("seller"),
                        "discount_type":        discount_type,
                        "idx_id":               supplier.get("campaign_id") or supplier.get("offer_id"),
                        "currency_id":          counter_currency.get("currency_id"),
                        "currency_value":       counter_currency.get("value"),
                    }
                )
        return discount_rows


    async def save_payment(self, payment_row: Dict, charge_rows: List[Dict]):
        """持久化支付主表 + 费用明细表。"""

        if not payment_row:
            return

        await DBManager.upsert(
            "mercado_payment",
            payment_row,
            conflict_cols=["seller_id", "payment_id"],
        )

        if charge_rows:
            await DBManager.upsert(
                "mercado_payment_charge",
                charge_rows,
                conflict_cols=["seller_id", "charge_id"],
            )


    async def save_discount(self, discount_rows: List[Dict]):
        """持久化折扣主表 + 商品明细表。"""

        if discount_rows:
            await DBManager.upsert(
                "mercado_discount",
                discount_rows,
                conflict_cols=["main_id", "idx_id"],
            )


    async def save_order(self, data: Dict):

        if not data:
            return {}

        order_rows      = data.get("order_rows") or []
        item_rows       = data.get("item_rows") or []
        payment_rows    = data.get("payment_rows") or []

        await DBManager.upsert("mercado_order", order_rows, ["seller_id","order_id"])

        order_ids = [row['order_id'] for row in order_rows]
        placeholders = ','.join(['%s'] * len(order_ids))

        rows = await DBManager.select(f"SELECT id as main_id,order_id,shipping_id FROM mercado_order WHERE order_id IN ({placeholders}) and seller_id = {self.shop.seller_id}", order_ids)
        id_map = {
            item['order_id']:item['main_id'] for item in rows
        }

        for item in item_rows:
            item['main_id'] = id_map.get(item['order_id'])

        for payment in payment_rows:
            payment['main_id'] = id_map.get(payment['order_id'])

        await DBManager.upsert("mercado_order_item", item_rows, ["main_id","item_id"])
        await DBManager.upsert("mercado_order_payment", payment_rows, ["main_id","payment_id"])

        return rows


    async def get_pack(self, PACK_ID: str):

        resp = await self.shop.request(
            method="GET",
            url=f"/packs/{PACK_ID}",
            headers={
                "Content-Type": "application/json",
            }
        )
        return resp


    async def get_order(self, ORDER_ID: str):

        resp = await self.shop.request(
            method="GET",
            url=f"/orders/{ORDER_ID}",
            headers={
                "Content-Type": "application/json",
            }
        )
        return resp


    async def get_shipment(self, SHIPMENT_ID: str):

        resp = await self.shop.request(
            method="GET",
            url=f"/shipments/{SHIPMENT_ID}",
            headers={
                "Content-Type": "application/json",
                "X-Format-New": "true",
            }
        )
        return resp


    async def get_shipment_history(self, SHIPMENT_ID: str):

        resp = await self.shop.request(
            method="GET",
            url=f"/shipments/{SHIPMENT_ID}/history",
            headers={
                "Content-Type": "application/json",
                "X-Format-New": "true",
            }
        )
        return resp


    async def get_shipment_sla(self, SHIPMENT_ID: str):

        resp = await self.shop.request(
            method="GET",
            url=f"/shipments/{SHIPMENT_ID}/sla",
            headers={
                "Content-Type": "application/json",
                "X-Format-New": "true",
            }
        )
        return resp


    async def get_payment(self, PAYMENT_ID: str):

        resp = await self.shop.request(
            method="GET",
            url=f"/v1/payments/{PAYMENT_ID}",
            other_url="https://api.mercadopago.com",
            headers={
                "Content-Type": "application/json",
                "X-Format-New": "true",
            }
        )
        return resp


    async def get_discount(self, ORDER_ID: str):

        resp = await self.shop.request(
            method="GET",
            url=f"/orders/{ORDER_ID}/discounts",
            headers={
                "Content-Type": "application/json",
            }
        )
        return resp


    async def search_order(self, search: Dict):

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
            params[gte_key] = at.isoformat()
            params[lte_key] = to.isoformat()
        else:
            raise ValueError("at 和 to 必须同时提供")

        resp = await self.shop.request(
            method="GET",
            url="/orders/search",
            params=params,
            headers={
                "Content-Type": "application/json",
            }
        )
        return resp


    async def sync_order(self, search: Dict):

        params_list = Order._build_params_(search)

        for params in params_list:

            limit   = params.get("limit", 50)
            offset  = params.get("offset", 0)
            total   = None

            while total is None or offset < total:

                params.update({"limit": limit, "offset": offset})

                resp = await self.shop.request(
                    method="GET",
                    url="/orders/search",
                    params=params,
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
                shipping_rows = await self.save_order(parsed)


                if not shipping_rows:
                    continue

                task_ment = []
                task_sla  = []
                task_discount = []

                for item in shipping_rows:
                    shipping_id = item.pop('shipping_id')
                    order_id    = item['order_id']
                    task_discount.append(self.get_discount(order_id))
                    task_ment.append(self.get_shipment(shipping_id))
                    task_sla.append(self.get_shipment_sla(shipping_id))

                resp_ment = await asyncio.gather(*task_ment, return_exceptions=True)
                shipment_parsed_list = []
                lead_time_parsed_list = []
                for item, resp in zip(shipping_rows, resp_ment):
                    if isinstance(resp, Exception):
                        continue
                    if isinstance(resp, Dict):
                        shipment_parsed,lead_time_parsed = self.parse_shipment(resp)
                        shipment_parsed.update(item)
                        lead_time_parsed.update(item)
                        shipment_parsed_list.append(shipment_parsed)
                        lead_time_parsed_list.append(lead_time_parsed)

                await DBManager.upsert("mercado_order_shipment", shipment_parsed_list, conflict_cols=["main_id"])
                await DBManager.upsert("mercado_shipment_lead", lead_time_parsed_list, conflict_cols=["main_id"])

                resp_sla = await asyncio.gather(*task_sla, return_exceptions=True)
                shipmentsla_parsed_list = []
                for item, resp in zip(shipment_parsed_list, resp_sla):
                    if isinstance(resp, Exception):
                        continue
                    if isinstance(resp, Dict):
                        shipment_parsed = self.parse_shipmentsla(resp)
                        shipment_parsed.update({"main_id": item["main_id"]})
                        shipmentsla_parsed_list.append(shipment_parsed)

                await DBManager.upsert("mercado_shipment_lead", shipmentsla_parsed_list, conflict_cols=["main_id"])

                resp_discount = await asyncio.gather(*task_discount, return_exceptions=True)
                discount_parsed_list = []
                for item, resp in zip(shipping_rows, resp_discount):
                    if isinstance(resp, Exception):
                        continue
                    if isinstance(resp, Dict):
                        discount_parsed = self.parse_discount(resp)
                        for row in discount_parsed:
                            row.update(item)
                        discount_parsed_list.extend(discount_parsed)

                await DBManager.upsert("mercado_order_discount", discount_parsed_list, conflict_cols=["main_id"])

                payment_ids = [item.get("payment_id") for item in parsed.get("payment_rows") or []]
                pago_task = [self.get_payment(payment_id) for payment_id in payment_ids]
                pago_resp = await asyncio.gather(*pago_task, return_exceptions=True)
                id_map = {
                    item["order_id"]: item["main_id"] for item in shipping_rows
                }
                payment_row_list = []
                charge_row_list = []
                for p in pago_resp:
                    if isinstance(p, Exception):
                        continue
                    if isinstance(p, Dict):
                        payment_row, charge_rows = self.parse_payment(p)
                        payment_row["main_id"] = id_map.get(payment_row["order_id"])
                        for charge_row in charge_rows:
                            charge_row["main_id"] = id_map.get(charge_row["order_id"])
                        payment_row_list.append(payment_row)
                        charge_row_list.extend(charge_rows)
                await DBManager.upsert("mercado_pago_payment", payment_row_list, conflict_cols=["main_id", "payment_id"])
                await DBManager.upsert("mercado_pago_payment_charge", charge_row_list, conflict_cols=["main_id", "charge_id"])
