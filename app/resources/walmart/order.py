"""Walmart 订单资源: Orders 请求 / 解析 / 存储 / 同步"""
from app.db.manager import DBManager
from app.platform.WalmartShop import WalmartShop
from typing import Dict, List
from app.core.converters import _json


class Order:
    """订单资源"""

    def __init__(self, shop: WalmartShop):
        self.shop = shop

    # ── 解析 ──────────────────────────────────────

    def parse(self, resp: List) -> Dict:
        """解析订单 API 响应 → order / order_line 两张表数据。"""

        if not resp:
            return {}

        shop_id = self.shop.shop_id

        order_rows:         list[dict] = []
        line_rows:          list[dict] = []

        for order in resp:

            shipping_info   = order.get("shippingInfo") or {}
            postal_address  = shipping_info.get("postalAddress") or {}
            ship_node       = order.get("shipNode") or {}
            order_lines     = order.get("orderLines") or {}
            order_line      = order_lines.get("orderLine") or []
            if isinstance(order_line, dict):
                order_line = [order_line]

            purchase_order_id = order.get("purchaseOrderId")

            # ── order 主表 ──────────────────────────
            order_rows.append({
                "shop_id":                  shop_id,
                "purchase_order_id":        purchase_order_id,
                "customer_order_id":        order.get("customerOrderId"),
                "customer_email_id":        order.get("customerEmailId"),
                "order_date":               order.get("orderDate"),
                "shipping_phone":           shipping_info.get("phone"),
                "estimated_delivery_date":  shipping_info.get("estimatedDeliveryDate"),
                "estimated_ship_date":      shipping_info.get("estimatedShipDate"),
                "method_code":              shipping_info.get("methodCode"),
                "carrier_method_name":      shipping_info.get("carrierMethodName"),
                "postal_name":              postal_address.get("name"),
                "postal_address1":          postal_address.get("address1"),
                "postal_address2":          postal_address.get("address2"),
                "postal_city":              postal_address.get("city"),
                "postal_state":             postal_address.get("state"),
                "postal_code":              postal_address.get("postalCode"),
                "postal_country":           postal_address.get("country"),
                "postal_address_type":      postal_address.get("addressType"),
                "shipnode_type":            ship_node.get("type"),
                "shipnode_name":            ship_node.get("name"),
                "shipnode_id":              ship_node.get("id"),
            })

            # ── order_line 子表 ─────────────────────
            for line in order_line:
                item            = line.get("item") or {}
                quantity        = line.get("orderLineQuantity") or {}
                refund          = line.get("refund") or {}
                fulfillment     = line.get("fulfillment") or {}

                charge          = ((line.get("charges") or {}).get("charge") or [{}])[0]
                orderLineStatus = ((line.get("orderLineStatuses") or {}).get("orderLineStatus") or [{}])[0]
                refundCharge    = ((refund.get("refundCharges") or {}).get("refundCharge") or [{}])[0]

                chargeAmount    = charge.get("chargeAmount") or {}
                chargeTax       = charge.get("tax") or {}
                taxAndOtherFees = charge.get("taxAndOtherFees") or {}
                taxAmount       = chargeTax.get("taxAmount") or {}

                statusQuantity  = orderLineStatus.get("statusQuantity") or {}
                trackingInfo    = orderLineStatus.get("trackingInfo") or {}
                carrierName     = trackingInfo.get("carrierName") or {}

                line_rows.append({
                    "purchase_order_id":                    purchase_order_id,
                    "line_number":                          line.get("lineNumber"),
                    "product_name":                         item.get("productName"),
                    "sku":                                  item.get("sku"),
                    "item_condition":                       item.get("condition"),
                    "ship_cross_border_enrolled":           1 if line.get("shipWithWalmartCrossBorderEnrolled") else 0,

                    "quantity_amount":                      quantity.get("amount"),
                    "quantity_unit":                        quantity.get("unitOfMeasurement"),
                    "status_date":                          line.get("statusDate"),


                    "fulfillment_option":                   fulfillment.get("fulfillmentOption"),
                    "fulfillment_ship_method":              fulfillment.get("shipMethod"),
                    "fulfillment_store_id":                 fulfillment.get("storeId"),
                    "fulfillment_pickup_datetime":          fulfillment.get("pickUpDateTime"),
                    "fulfillment_pickup_by":                fulfillment.get("pickUpBy"),
                    "fulfillment_shipping_programtype":     fulfillment.get("shippingProgramType"),

                    "charge_type":                          charge.get("chargeType"),
                    "charge_name":                          charge.get("chargeName"),
                    "charge_amount":                        chargeAmount.get("amount"),
                    "charge_currency":                      chargeAmount.get("currency"),
                    "tax_name":                             chargeTax.get("taxName"),
                    "tax_amount":                           taxAmount.get("amount"),
                    "tax_currency":                         taxAmount.get("currency"),
                    "tax_and_other_fees_name":              taxAndOtherFees.get("taxAndOtherFeesName"),
                    "tax_and_other_fees_amount":            (taxAndOtherFees.get("taxAndOtherFeesAmount") or {}).get("amount"),
                    "tax_and_other_fees_currency":          (taxAndOtherFees.get("taxAndOtherFeesAmount") or {}).get("currency"),

                    "status":                               orderLineStatus.get("status"),
                    "sub_seller_id":                        orderLineStatus.get("subSellerId"),
                    "unit_of_measurement":                  statusQuantity.get("unitOfMeasurement"),
                    "amount":                               statusQuantity.get("amount"),
                    "cancellation_reason":                  orderLineStatus.get("cancellationReason"),
                    "ship_datetime":                        trackingInfo.get("shipDateTime"),
                    "other_carrier":                        carrierName.get("otherCarrier"),
                    "carrier":                              carrierName.get("carrier"),
                    "method_code":                          trackingInfo.get("methodCode"),
                    "carrier_method_code":                  trackingInfo.get("carrierMethodCode"),
                    "tracking_number":                      trackingInfo.get("trackingNumber"),
                    "tracking_url":                         trackingInfo.get("trackingURL"),
                    "return_center_address":                orderLineStatus.get("returnCenterAddress"),

                    "refund_id":                            refund.get("refundId"),
                    "refund_comments":                      refund.get("refundComments"),
                    "refund_reason":                        refundCharge.get("refundReason"),
                    "refund_charge_type":                   (refundCharge.get("charge") or {}).get("chargeType"),
                    "refund_charge_name":                   (refundCharge.get("charge") or {}).get("chargeName"),
                    "refund_charge_amount":                 ((refundCharge.get("charge") or {}).get("chargeAmount") or {}).get("amount"),
                    "refund_charge_currency":               ((refundCharge.get("charge") or {}).get("chargeAmount") or {}).get("currency"),
                    "refund_tax":                           _json((refundCharge.get("charge") or {}).get("tax")),
                    "refund_tax_and_other_fees":            _json((refundCharge.get("charge") or {}).get("taxAndOtherFees")),
                })

        return {
            "order_rows":       order_rows,
            "line_rows":        line_rows,
        }

    # ── 查询 ──────────────────────────────────────

    async def search(self, search: Dict):

        resp = await self.shop.request(
            method  = "GET",
            url     = "/v3/orders",
            params  = search,
        )

        return resp

    # ── 存储 ──────────────────────────────────────

    async def save(self, data: Dict):
        """持久化解析后的订单数据（2 张表）。"""
        if not data:
            return

        order_rows          = data.get("order_rows")        or []
        line_rows           = data.get("line_rows")         or []


        flag = await DBManager.upsert("walmart_order", order_rows, ["shop_id", "purchase_order_id"])

        if flag is not None:
            pass

        ids = [item["purchase_order_id"] for item in order_rows]
        if not ids:
            return
        placeholders = ",".join(["%s"] * len(ids))

        rows = await DBManager.select(
            f"SELECT id AS main_id, purchase_order_id FROM walmart_order "
            f"WHERE shop_id = %s AND purchase_order_id IN ({placeholders})",
            [self.shop.shop_id] + ids,
        )

        id_map = {row["purchase_order_id"]: row["main_id"] for row in rows}



        for line in line_rows:
            line["main_id"] = id_map[line["purchase_order_id"]]

        await DBManager.upsert("walmart_order_line", line_rows, ["main_id", "line_number"])


    # ── 同步 ──────────────────────────────────────

    async def sync(self, search: Dict):
        """全量同步订单（自动翻页）。"""

        params = Order._build_param(search)

        totalCount = None
        nextCursor = ""

        has_more = True
        while has_more:

            url = "/v3/orders" + nextCursor

            resp = await self.shop.request(
                method  = "GET",
                url     = url,
                params  = params,
            )

            if totalCount is None:
                totalCount = ((resp.get("list") or {}).get("meta") or {}).get("totalCount") or 0
                if totalCount == 0:
                    has_more = False
                    return

            nextCursor = ((resp.get("list") or {}).get("meta") or {}).get("nextCursor") or ""

            if not nextCursor:
                has_more = False
                return

            order  = ((resp.get("list") or {}).get("elements") or {}).get("order") or []
            if not order:
                has_more = False
                return

            parsed = self.parse(order)
            await self.save(parsed)

    # ── 参数构建 ──────────────────────────────────

    @staticmethod
    def _build_param(search: Dict) -> Dict:
        """将搜索参数按日期范围拆分为多个分页请求的参数列表。"""

        datatype = search.get("datatype")
        at = search.get("at")
        to = search.get("to")

        params = {k: v for k, v in search.items() if k not in ("at", "to", "datatype")}

        date_fields = {
            0: ("lastModifiedStartDate", "lastModifiedEndDate"),
            1: ("createdStartDate", "createdEndDate"),
            2: ("fromExpectedShipDate", "toExpectedShipDate"),
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
