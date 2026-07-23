"""Ripley 订单资源: Orders 请求 / 解析 / 存储 / 同步"""
from datetime import timedelta
from app.db.manager import DBManager
from app.platform.RipleyShop import RipleyShop
from typing import Dict, List
from app.core.converters import _trim, _json


class Order:
    """订单资源（无 QPM 需求，直接使用共享 session）。"""

    def __init__(self, shop: RipleyShop):
        self.shop = shop

    # ── 解析 ──────────────────────────────────────

    def parse(self, resp: Dict) -> Dict:
        """解析订单 API 响应 → order / customer / address / contact / order_line / cancelation / refund 多表数据。"""

        if not resp:
            return {}

        orders = resp.get("orders") or []
        if isinstance(orders, dict):
            orders = [orders]

        shop_id = self.shop.shop_id

        order_rows:         list[dict] = []
        customer_rows:      list[dict] = []
        line_rows:          list[dict] = []
        cancelation_rows:   list[dict] = []
        refund_rows:        list[dict] = []

        for order in orders:
            order_id = order.get("order_id")

            # ── 子对象解包 ──────────────────────────
            channel         = order.get("channel") or {}
            customer        = order.get("customer") or {}
            delivery_date   = order.get("delivery_date") or {}
            fulfillment     = order.get("fulfillment") or {}
            invoice_details = order.get("invoice_details") or {}
            references      = order.get("references") or {}
            promotions      = order.get("promotions") or {}

            order_lines     = order.get("order_lines") or []
            order_taxes     = order.get("order_taxes") or []

            # ── order 主表 ──────────────────────────
            order_rows.append({
                "shop_id":                              shop_id,
                "order_id":                             order_id,
                "acceptance_decision_date":             _trim(order.get("acceptance_decision_date")),
                "can_cancel":                           1 if order.get("can_cancel") else 0,
                "can_shop_ship":                        1 if order.get("can_shop_ship") else 0,
                "channel_code":                         channel.get("code"),
                "channel_label":                        channel.get("label"),
                "commercial_id":                        order.get("commercial_id"),
                "created_date":                         _trim(order.get("created_date")),
                "currency_iso_code":                    order.get("currency_iso_code"),
                "customer_debited_date":                _trim(order.get("customer_debited_date")),
                "customer_directly_pays_seller":        1 if order.get("customer_directly_pays_seller") else 0,
                "customer_notification_email":          order.get("customer_notification_email"),
                "delivery_date_earliest":               _trim(delivery_date.get("earliest")),
                "delivery_date_latest":                 _trim(delivery_date.get("latest")),
                "discount_campaigns":                   _json(order.get("discount_campaigns")),
                "fulfillment_center_code":              (fulfillment.get("center") or {}).get("code"),
                "fully_refunded":                       1 if order.get("fully_refunded") else 0,
                "has_customer_message":                 1 if order.get("has_customer_message") else 0,
                "has_incident":                         1 if order.get("has_incident") else 0,
                "has_invoice":                          1 if order.get("has_invoice") else 0,
                "invoice_details":                      _json(invoice_details),
                "last_updated_date":                    _trim(order.get("last_updated_date")),
                "leadtime_to_ship":                     order.get("leadtime_to_ship"),
                "order_additional_fields":              _json(order.get("order_additional_fields")),
                "order_state":                          order.get("order_state"),
                "order_state_reason_code":              order.get("order_state_reason_code"),
                "order_state_reason_label":             order.get("order_state_reason_label"),
                "order_tax_mode":                       order.get("order_tax_mode"),
                "order_taxes":                          _json(order_taxes),
                "payment_type":                         order.get("payment_type"),
                "payment_workflow":                     order.get("payment_workflow"),
                "price":                                order.get("price"),
                "promotions":                           _json(promotions),
                "quote_id":                             order.get("quote_id"),
                "reference_for_customer":               references.get("order_reference_for_customer"),
                "reference_for_seller":                 references.get("order_reference_for_seller"),
                "shipping_carrier_code":                order.get("shipping_carrier_code"),
                "shipping_carrier_standard_code":       order.get("shipping_carrier_standard_code"),
                "shipping_company":                     order.get("shipping_company"),
                "shipping_deadline":                    _trim(order.get("shipping_deadline")),
                "shipping_price":                       order.get("shipping_price"),
                "shipping_pudo_id":                     order.get("shipping_pudo_id"),
                "shipping_tracking":                    order.get("shipping_tracking"),
                "shipping_tracking_url":                order.get("shipping_tracking_url"),
                "shipping_type_code":                   order.get("shipping_type_code"),
                "shipping_type_label":                  order.get("shipping_type_label"),
                "shipping_type_standard_code":          order.get("shipping_type_standard_code"),
                "shipping_zone_code":                   order.get("shipping_zone_code"),
                "shipping_zone_label":                  order.get("shipping_zone_label"),
                "total_commission":                     order.get("total_commission"),
                "total_price":                          order.get("total_price"),
                "transaction_date":                     _trim(order.get("transaction_date")),
                "transaction_number":                   order.get("transaction_number"),
            })

            billing_address = customer.get("billing_address") or {}
            customer_rows.append({
                "order_id":                 order_id,
                "accounting_contact":       _json(customer.get("accounting_contact")),
                "city":                     billing_address.get("city"),
                "company":                  billing_address.get("company"),
                "company_2":                billing_address.get("company_2"),
                "country":                  billing_address.get("country"),
                "country_iso_code":         billing_address.get("country_iso_code"),
                "billing_address_firstname":billing_address.get("firstname"),
                "billing_address_lastname": billing_address.get("lastname"),
                "state":                    billing_address.get("state"),
                "street_1":                 billing_address.get("street_1"),
                "street_2":                 billing_address.get("street_2"),
                "zip_code":                 billing_address.get("zip_code"),
                "civility":                 customer.get("civility"),
                "customer_id":              customer.get("customer_id"),
                "delivery_contact":         _json(customer.get("delivery_contact")),
                "firstname":                customer.get("firstname"),
                "lastname":                 customer.get("lastname"),
                "locale":                   customer.get("locale"),
                "organization":             _json(customer.get("organization")),
                "shipping_address":         _json(customer.get("shipping_address")),
            })
            # ── order_line 子表 ─────────────────────
            for line in order_lines:
                order_line_id = line.get("order_line_id")
                shipping_from = line.get("shipping_from") or {}
                cancelations  = line.get("cancelations")  or []
                refunds       = line.get("refunds")       or []

                line_rows.append({
                    "order_id":                         order_id,
                    "order_line_id":                    order_line_id,
                    "can_refund":                       1 if line.get("can_refund") else 0,
                    "category_code":                    line.get("category_code"),
                    "category_label":                   line.get("category_label"),
                    "commission_fee":                   line.get("commission_fee"),
                    "commission_rate_vat":              line.get("commission_rate_vat"),
                    "commission_taxes":                 _json(line.get("commission_taxes")),
                    "commission_vat":                   line.get("commission_vat"),
                    "created_date":                     _trim(line.get("created_date")),
                    "debited_date":                     _trim(line.get("debited_date")),
                    "description":                      line.get("description"),
                    "fees":                             _json(line.get("fees")),
                    "last_updated_date":                _trim(line.get("last_updated_date")),
                    "offer_id":                         line.get("offer_id"),
                    "offer_sku":                        line.get("offer_sku"),
                    "offer_state_code":                 line.get("offer_state_code"),
                    "order_line_additional_fields":     _json(line.get("order_line_additional_fields")),
                    "order_line_index":                 line.get("order_line_index"),
                    "order_line_state":                 line.get("order_line_state"),
                    "order_line_state_reason_code":     line.get("order_line_state_reason_code"),
                    "order_line_state_reason_label":    line.get("order_line_state_reason_label"),
                    "origin_unit_price":                line.get("origin_unit_price"),
                    "price":                            line.get("price"),
                    "price_additional_info":            line.get("price_additional_info"),
                    "price_amount_breakdown":           _json(line.get("price_amount_breakdown")),
                    "price_unit":                       line.get("price_unit"),
                    "product_medias":                   _json(line.get("product_medias")),
                    "product_shop_sku":                 line.get("product_shop_sku"),
                    "product_sku":                      line.get("product_sku"),
                    "product_title":                    line.get("product_title"),
                    "promotions":                       _json(line.get("promotions")),
                    "quantity":                         line.get("quantity"),
                    "received_date":                    _trim(line.get("received_date")),
                    "shipped_date":                     _trim(line.get("shipped_date")),
                    "shipping_from":                    _json(shipping_from),
                    "shipping_price":                   line.get("shipping_price"),
                    "shipping_price_additional_unit":   line.get("shipping_price_additional_unit"),
                    "shipping_price_amount_breakdown":  _json(line.get("shipping_price_amount_breakdown")),
                    "shipping_price_unit":              line.get("shipping_price_unit"),
                    "shipping_taxes":                   _json(line.get("shipping_taxes")),
                    "taxes":                            _json(line.get("taxes")),
                    "total_commission":                 line.get("total_commission"),
                    "total_price":                      line.get("total_price"),
                })

                # ── cancelation 子表（line 之下）─────
                for cancel in cancelations:
                    purchase_information = cancel.get("purchase_information") or {}
                    cancelation_rows.append({
                        "order_id":                         order_id,
                        "order_line_id":                    order_line_id,
                        "cancelation_id":                   cancel.get("id"),
                        "amount":                           cancel.get("amount"),
                        "amount_breakdown":                 _json(cancel.get("amount_breakdown")),
                        "commission_amount":                cancel.get("commission_amount"),
                        "commission_taxes":                 _json(cancel.get("commission_taxes")),
                        "commission_total_amount":          cancel.get("commission_total_amount"),
                        "created_date":                     _trim(cancel.get("created_date")),
                        "fees":                             _json(cancel.get("fees")),
                        "purchase_commission_on_fees":      (purchase_information.get("purchase_commission_on_fees") or {}).get("total_amount"),
                        "purchase_commission_on_price":     purchase_information.get("purchase_commission_on_price"),
                        "purchase_commission_on_shipping":  purchase_information.get("purchase_commission_on_shipping"),
                        "purchase_fee_amount":              (purchase_information.get("purchase_fee_amount") or {}).get("total_amount"),
                        "purchase_price":                   purchase_information.get("purchase_price"),
                        "purchase_shipping_price":          purchase_information.get("purchase_shipping_price"),
                        "quantity":                         cancel.get("quantity"),
                        "reason_code":                      cancel.get("reason_code"),
                        "shipping_amount":                  cancel.get("shipping_amount"),
                        "shipping_amount_breakdown":        _json(cancel.get("shipping_amount_breakdown")),
                        "shipping_taxes":                   _json(cancel.get("shipping_taxes")),
                        "taxes":                            _json(cancel.get("taxes")),
                    })

                # ── refund 子表（line 之下）─────────

                for refund in refunds:
                    refund_rows.append({
                        "order_id":                 order_id,
                        "order_line_id":            order_line_id,
                        "refund_id":                refund.get("id"),
                        "order_refund_id":          refund.get("order_refund_id"),
                        "amount":                   refund.get("amount"),
                        "commission_amount":        refund.get("commission_amount"),
                        "commission_tax_amount":    refund.get("commission_tax_amount"),
                        "commission_taxes":         _json(refund.get("commission_taxes")),
                        "commission_total_amount":  refund.get("commission_total_amount"),
                        "created_date":             _trim(refund.get("created_date")),
                        "fees":                     _json(refund.get("fees")),
                        "quantity":                 refund.get("quantity"),
                        "reason_code":              refund.get("reason_code"),
                        "shipping_amount":          refund.get("shipping_amount"),
                        "shipping_taxes":           _json(refund.get("shipping_taxes")),
                        "state":                    refund.get("state"),
                        "tax_legal_notice":         refund.get("tax_legal_notice"),
                        "taxes":                    _json(refund.get("taxes")),
                    })

        return {
            "order_rows":           order_rows,
            "customer_rows":        customer_rows,
            "line_rows":            line_rows,
            "cancelation_rows":     cancelation_rows,
            "refund_rows":          refund_rows,
        }

    # ── 查询 ──────────────────────────────────────

    async def search(self, search: Dict):

        params = Order._paese_params(search)

        resp = await self.shop.request(
            method  = "GET",
            url     = "/api/orders",
            params  = params,
        )

        return resp

    # ── 存储 ──────────────────────────────────────

    async def save(self, data: Dict):
        """持久化解析后的订单数据（5 张表）。"""

        if not data:
            return

        order_rows          = data.get("order_rows") or []
        customer_rows       = data.get("customer_rows") or []
        line_rows           = data.get("line_rows") or []
        cancelation_rows    = data.get("cancelation_rows") or []
        refund_rows         = data.get("refund_rows") or []

        # ── order 主表 ────────────────────────────
        flag = await DBManager.upsert("ripley_order", order_rows, ["shop_id", "order_id"])

        if flag is not None:
            pass

        # ── 查回自增 id，供子表 main_id 外键 ──────
        order_ids = [r["order_id"] for r in order_rows]
        if not order_ids:
            return
        placeholders = ",".join(["%s"] * len(order_ids))
        rows = await DBManager.select(
            f"SELECT id AS main_id, order_id FROM ripley_order "
            f"WHERE shop_id = %s AND order_id IN ({placeholders})",
            [self.shop.shop_id] + order_ids,
        )
        id_map = {r["order_id"]: r["main_id"] for r in rows}

        if customer_rows:
            for row in customer_rows:
                row["main_id"] = id_map.get(row["order_id"])
            await DBManager.upsert("ripley_order_customer", customer_rows, ["main_id"])
        if line_rows:
            for row in line_rows:
                row["main_id"] = id_map.get(row["order_id"])
            await DBManager.upsert("ripley_order_line", line_rows, ["main_id", "order_line_id"])

        if cancelation_rows:
            for row in cancelation_rows:
                row["main_id"] = id_map.get(row["order_id"])
            await DBManager.upsert("ripley_order_line_cancelation", cancelation_rows, ["main_id", "order_line_id", "cancelation_id"])
        if refund_rows:
            for row in refund_rows:
                row["main_id"] = id_map.get(row["order_id"])
            await DBManager.upsert("ripley_order_line_refund", refund_rows, ["main_id", "order_line_id", "refund_id"])

    # ── 同步 ──────────────────────────────────────

    async def sync(self, search: Dict):
        """全量同步订单（自动翻页）。"""

        params_list = Order._build_params(search)

        for params in params_list:
            limit   = params.get("max", 100)
            offset  = params.get("offset", 0)
            total   = None

            while total is None or offset < total:

                params.update({"max": limit, "offset": offset})

                resp = await self.shop.request(
                    method  = "GET",
                    url     = "/api/orders",
                    params  = params,
                )

                offset += limit

                if total is None:
                    total = resp.get("total_count", 0) or 0
                    if total == 0:
                        break

                orders = resp.get("orders") or []
                if not orders:
                    break

                parsed = self.parse(resp) or {}
                await self.save(parsed)


    @staticmethod
    def _build_params(search: Dict) -> List[Dict]:
        """将搜索参数按日期范围拆分为多个分页请求的参数列表。"""

        datatype = search.get("datatype")
        at = search.get("at")
        to = search.get("to")

        params = {k: v for k, v in search.items() if k not in ("at", "to", "datatype")}

        params_list = []

        date_fields = {
            0: ("start_update_date", "end_update_date"),
            1: ("start_date", "end_date"),
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
                current_at = current_to

            return params_list
        else:
            raise ValueError("at 和 to 必须同时提供")


    @staticmethod
    def _paese_params(search: Dict) -> Dict:
        """将搜索参数按日期范围拆分为多个分页请求的参数列表。"""

        datatype = search.get("datatype")
        at = search.get("at")
        to = search.get("to")

        params = {k: v for k, v in search.items() if k not in ("at", "to", "datatype")}

        date_fields = {
            0: ("start_update_date", "end_update_date"),
            1: ("start_date", "end_date"),
        }

        if datatype not in date_fields:
            raise ValueError(f"不支持的 datatype: {datatype}")

        gte_key, lte_key = date_fields[datatype]

        if at and to:

            params[gte_key] = at.isoformat()
            params[lte_key] = to.isoformat()
            return params
        else:
            raise ValueError("at 和 to 必须同时提供")
