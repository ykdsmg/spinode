"""Paris 订单资源: Orders 请求 / 解析 / 存储 / 同步"""
import json

import aiohttp
from datetime import datetime, timedelta
from app.db.manager import DBManager
from app.platform.ParisShop import ParisShop

from app.core.converters import _trim


class Order:
    """订单资源（无 QPM 需求，直接使用共享 session）。"""

    def __init__(self, shop: ParisShop) -> None:
        self.shop = shop

    # ── 解析 ──────────────────────────────────────

    def parse(self, origin: dict) -> dict:
        """解析订单 API 响应 → order / sub_order / item 三表数据。"""
        listado = origin.get("data") or []
        if isinstance(listado, dict):
            listado = [listado]

        order_rows: list[dict] = []
        sub_order_rows: list[dict] = []
        item_rows: list[dict] = []
        billing_address_rows: list[dict] = []

        seller_id = self.shop.seller_id

        for order in listado:
            # ── 展平一级字段 ──
            customer = order.get("customer") or {}
            billing = order.get("billingAddress") or {}
            businessInvoice = order.get("businessInvoice") or {}
            subOrders = order.get("subOrders") or []

            order_rows.append({
                "seller_id":          seller_id,
                "order_id":           order.get("id"),
                "origin":             order.get("origin"),
                "origin_order_number":order.get("originOrderNumber"),
                "sub_order_number":   order.get("subOrderNumber"),
                "origin_invoice_type":order.get("originInvoiceType"),
                "origin_order_date":  _trim(order.get("originOrderDate")),
                "created_at":         _trim(order.get("createdAt")),
                "customer_id":        customer.get("id"),
                "customer_name":      customer.get("name"),
                "customer_email":     customer.get("email"),
                "customer_doc_type":  customer.get("documentType"),
                "customer_doc_number":customer.get("documentNumber"),
                "business_invoice_id":businessInvoice.get("id"),
                "business_name":      businessInvoice.get("businessName"),
                "company_rut":        businessInvoice.get("companyRut"),
                "business_area":      businessInvoice.get("businessArea"),
                "address":            businessInvoice.get("address"),
                "comuna":             businessInvoice.get("comuna"),
                "region":             businessInvoice.get("region"),
                "email":              businessInvoice.get("email"),

            })
            billing_address_rows.append({
                "order_id":           order.get("id"),
                "sub_order_number":   order.get("subOrderNumber"),
                "billing_address_id": billing.get("id"),
                "first_name":         billing.get("firstName"),
                "last_name":          billing.get("lastName"),
                "address1":           billing.get("address1"),
                "address2":           billing.get("address2"),
                "address3":           billing.get("address3"),
                "city":               billing.get("city"),
                "state_code":         billing.get("stateCode"),
                "country_code":       billing.get("countryCode"),
                "phone":              billing.get("phone"),
                "communa_code":       billing.get("communaCode"),
                "additional_info":    billing.get("additionalInfo"),
                "pick_up_store_id":   billing.get("pickUpStoreId"),
            })

            # ── 子订单 ──
            for sub in subOrders:
                delivery = sub.get("deliveryOption") or {}
                status   = sub.get("status") or {}

                sub_order_rows.append({
                    "sub_order_id":           sub.get("id"),
                    "sub_order_number":       sub.get("subOrderNumber"),
                    "status_id":              sub.get("statusId"),
                    "carrier":                sub.get("carrier"),
                    "tracking_number":        sub.get("trackingNumber"),
                    "label_id":               sub.get("labelId"),
                    "delivery_external_id":   sub.get("deliveryExternalId"),
                    "dispatch_date":          _trim(sub.get("dispatchDate")),
                    "arrival_date":           _trim(sub.get("arrivalDate")),
                    "arrival_date_end":       _trim(sub.get("arrivalDateEnd")),
                    "effective_arrival_date": _trim(sub.get("effectiveArrivalDate")),
                    "effective_dispatch_date":_trim(sub.get("effectiveDispatchDate")),
                    "effective_manifest_date":_trim(sub.get("effectiveManifestDate")),
                    "last_notification_id":   sub.get("lastNotificationId"),
                    "fulfillment":            sub.get("fulfillment"),
                    "cost":                   sub.get("cost"),
                    "updated_at":             _trim(sub.get("updatedAt")),
                    "summary_id":             sub.get("summaryId"),
                    "facility_config_id":     sub.get("facilityConfigId"),
                    "bocbol_order_id":        sub.get("bocbolOrderId"),
                    "is_splitted":            sub.get("isSplitted"),
                    "origin_order_number":    sub.get("originOrderNumber"),
                    "origin_invoice_type":    sub.get("originInvoiceType"),
                    "origin_order_date":      _trim(sub.get("originOrderDate")),
                    "origin":                 sub.get("origin"),
                    "delivery_option_id":     delivery.get("id"),
                    "delivery_option_name":   delivery.get("name"),
                    "delivery_option_desc":   delivery.get("description"),
                    "delivery_option_trans":  delivery.get("translate"),
                    "status_name":            status.get("name"),
                    "status_desc":            status.get("description"),
                    "status_trans":           status.get("translate"),
                    "status_cancelable":      status.get("cancelable"),
                    "order_type_id":          sub.get("orderTypeId"),
                })

                # ── 商品行 ──
                for item in sub.get("items") or []:
                    st   = item.get("status") or {}
                    cat  = item.get("categoryObj") or {}
                    cancellationReason = item.get("cancellationReason") or {}

                    item_rows.append({
                        "item_id":                item.get("id"),
                        "sku":                    item.get("sku"),
                        "name":                   item.get("name"),
                        "seller_id":              item.get("sellerId"),
                        "jda_sku":                item.get("jdaSku"),
                        "base_price":             item.get("basePrice"),
                        "gross_price":            item.get("grossPrice"),
                        "price_after_discounts":  item.get("priceAfterDiscounts"),
                        "tax_rate":               item.get("taxRate"),
                        "size":                   item.get("size"),
                        "seller_sku":             item.get("sellerSku"),
                        "tax":                    item.get("tax"),
                        "position":               item.get("position"),
                        "tax_basis":              item.get("taxBasis"),
                        "commission":             item.get("commission"),
                        "sub_order_number":       item.get("subOrderNumber"),
                        "reconditioned":          item.get("reconditioned"),
                        "cancel_reason_id":       item.get("cancellationReasonId"),
                        "status_id":              item.get("statusId"),
                        "image_path":             item.get("imagePath"),
                        "item_size":              item.get("itemSize"),
                        "return_id":              item.get("returnId"),
                        "user_id":                item.get("userId"),
                        "shipping_cost":          item.get("shippingCost"),
                        "external_category_id":   item.get("externalCategoryId"),
                        "status_name":            st.get("name"),
                        "status_desc":            st.get("description"),
                        "status_trans":           st.get("translate"),
                        "status_cancelable":      st.get("cancelable"),
                        "cancel_reason":          cancellationReason.get("name"),
                        "return":                 item.get("return"),
                        "category_obj_id":        cat.get("id"),
                        "category_obj_name":      cat.get("name"),
                        "category_obj_code":      cat.get("code"),
                        "category_obj_weight":    cat.get("weight"),
                        "category_obj_ext_cat_id":cat.get("externalCategoryId"),
                        "order_id":               item.get("orderId"),
                    })

        return {
            "orderRows": order_rows,
            "subOrderRows": sub_order_rows,
            "itemRows": item_rows,
            "billingAddressRows": billing_address_rows,
        }

    # ── 存储 ──────────────────────────────────────

    async def save(self, data: dict):
        if not data:
            return
        order_rows = data.get("orderRows") or []
        sub_rows   = data.get("subOrderRows") or []
        item_rows  = data.get("itemRows") or []
        billing_address_rows = data.get("billingAddressRows") or []

        # order 表

        await DBManager.upsert("paris_order", order_rows, ["order_id"])

        # 查回自增 id，供子表 main_id 外键
        order_numbers = [r["sub_order_number"] for r in order_rows]
        placeholders  = ",".join(["%s"] * len(order_numbers))
        rows = await DBManager.select(
            f"SELECT id, sub_order_number FROM paris_order "
            f"WHERE seller_id = %s AND sub_order_number IN ({placeholders})",
            [self.shop.seller_id] + order_numbers,
        )
        id_map = {r["sub_order_number"]: r["id"] for r in rows}
        for row in billing_address_rows:
            row["main_id"] = id_map.get(row["sub_order_number"])
        for row in sub_rows:
            row["main_id"] = id_map.get(row["sub_order_number"])
        for row in item_rows:
            row["main_id"] = id_map.get(row["sub_order_number"])

        if billing_address_rows:
            await DBManager.upsert("paris_order_address_billing", billing_address_rows, ["main_id"])
        if sub_rows:
            await DBManager.upsert("paris_sub_order", sub_rows, ["main_id", "sub_order_id"])
        if item_rows:
            await DBManager.upsert("paris_order_item", item_rows, ["seller_id", "item_id"])




    # ── 同步 ──────────────────────────────────────

    async def sync(self, session: aiohttp.ClientSession, search: dict):
        datatype = search.get("datatype")
        at_str   = search.pop("at") if search.get("at") is not None else None
        to_str   = search.pop("to") if search.get("to") is not None else None
        at       = datetime.strptime(at_str, "%Y-%m-%d") if at_str else (datetime.now() - timedelta(days=1)).date()
        to       = datetime.strptime(to_str, "%Y-%m-%d") if to_str else datetime.now().date()
        if datatype is None:
            at = to = datetime.now().date()

        flag = True
        while flag or at < to:
            if datatype is not None:
                if flag:
                    search.pop("datatype")
                    flag = False
                if datatype == 0:
                    search["gteUpdatedAt"] = at.strftime("%Y-%m-%d")
                    at += timedelta(days=1)
                    search["lteUpdatedAt"] = at.strftime("%Y-%m-%d")
                elif datatype == 1:
                    search["gteCreatedAt"] = at.strftime("%Y-%m-%d")
                    at += timedelta(days=1)
                    search["lteCreatedAt"] = at.strftime("%Y-%m-%d")
                elif datatype == 2:
                    search["gteCreatedAtInOrigin"] = at.strftime("%Y-%m-%d")
                    at += timedelta(days=1)
                    search["lteCreatedAtInOrigin"] = at.strftime("%Y-%m-%d")
            else:
                flag = False

            limit = 100
            offset = 0
            count = 0
            first = True

            while first or offset < count:
                search["limit"] = limit
                search["offset"] = offset

                resp = await self.shop.request(
                    session=session, method="GET", url="/v1/orders", params=search
                )

                if first:
                    first = False
                    count = int(resp.get("count", 0)) or 0
                    if count == 0:
                        break
                if resp:
                    offset += limit
                    parsed = self.parse(resp) or {}
                    with open(f"data/parsed_orders_{offset}.json", "w", encoding="utf-8") as f:
                        json.dump(parsed, f, ensure_ascii=False, indent=4)
                    await self.save(parsed)

    async def searchorder(self, session: aiohttp.ClientSession, search: dict):
        datatype = search.get("datatype")
        at_str   = search.pop("at") if search.get("at") is not None else None
        to_str   = search.pop("to") if search.get("to") is not None else None
        at       = datetime.strptime(at_str, "%Y-%m-%d") if at_str else (datetime.now() - timedelta(days=1)).date()
        to       = datetime.strptime(to_str, "%Y-%m-%d") if to_str else datetime.now().date()

        if datatype is not None:
            search.pop("datatype")
            if datatype == 0:
                search["gteUpdatedAt"] = at.strftime("%Y-%m-%d")
                search["lteUpdatedAt"] = to.strftime("%Y-%m-%d")
            elif datatype == 1:
                search["gteCreatedAt"] = at.strftime("%Y-%m-%d")
                search["lteCreatedAt"] = to.strftime("%Y-%m-%d")
            elif datatype == 2:
                search["gteCreatedAtInOrigin"] = to.strftime("%Y-%m-%d")
                search["lteCreatedAtInOrigin"] = to.strftime("%Y-%m-%d")

        search["limit"] = 10
        search["offset"] = 0
        resp = await self.shop.request(
            session=session, method="GET", url="/v1/orders", params=search
        )
        return resp
