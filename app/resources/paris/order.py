"""Paris 订单资源: Orders 请求 / 解析 / 存储 / 同步"""

from datetime import datetime, timedelta

from app.db.manager import DBManager
from app.http.client import HttpClient
from app.platform.ParisShop import ParisShop


class Order:
    """商品资源。"""

    def __init__(self, shop: ParisShop, qpm: int | None = None) -> None:
        self.shop = shop
        self.client = HttpClient()

    def parse(self, origin: dict):
        listado = origin.get("data") or []
        if isinstance(listado, dict):
            listado = [listado]

        order_data = []
        sub_order_data = []
        items_data = []
        for order in listado:
            # data 字段
            originOrderDate = order.get("originOrderDate")
            createdAt = order.get("createdAt")
            # dict 字段
            customer = order.get("customer") or {}
            billingAddress = order.get("billingAddress") or {}
            # list 字段
            subOrders = order.get("subOrders") or []

            order_info = {
                "id": order.get("id"),
                "origin": order.get("origin"),
                "originOrderNumber": order.get("originOrderNumber"),
                "subOrderNumber": order.get("subOrderNumber"),
                "originInvoiceType": order.get("originInvoiceType"),
                "originOrderDate": originOrderDate[:19] if originOrderDate else None,
                "createdAt": createdAt[:19] if createdAt else None,
                "customerId": customer.get("id"),
                "customerName": customer.get("name"),
                "customerEmail": customer.get("email"),
                "customerDocumentType": customer.get("documentType"),
                "customerDocumentNumber": customer.get("documentNumber"),
                "businessInvoice": order.get("businessInvoice"),
                "billingAddressId": billingAddress.get("id"),
                "firstName": billingAddress.get("firstName"),
                "lastName": billingAddress.get("lastName"),
                "address1": billingAddress.get("address1"),
                "address2": billingAddress.get("address2"),
                "address3": billingAddress.get("address3"),
                "city": billingAddress.get("city"),
                "stateCode": billingAddress.get("stateCode"),
                "countryCode": billingAddress.get("countryCode"),
                "phone": billingAddress.get("phone"),
                "communaCode": billingAddress.get("communaCode"),
                "additionalInfo": billingAddress.get("additionalInfo"),
                "pickUpStoreId": billingAddress.get("pickUpStoreId")
            }
            order_data.append(order_info)

            for suborder in subOrders:
                deliveryOption = suborder.get("deliveryOption") or {}
                status = suborder.get("status") or {}
                items = suborder.get("items") or []
                # date
                dispatchDate = suborder.get("dispatchDate") or None
                arrivalDate = suborder.get("arrivalDate") or None
                arrivalDateEnd = suborder.get("arrivalDateEnd") or None
                effectiveArrivalDate = suborder.get("effectiveArrivalDate") or None
                effectiveDispatchDate = suborder.get("effectiveDispatchDate") or None
                effectiveManifestDate = suborder.get("effectiveManifestDate") or None
                updatedAt = suborder.get("updatedAt") or None
                originOrderDate = suborder.get("originOrderDate") or None
                suborder_info = {
                    "id": suborder.get("id"),
                    "subOrderNumber": suborder.get("subOrderNumber"),
                    "statusId": suborder.get("statusId"),
                    "carrier": suborder.get("carrier"),
                    "trackingNumber": suborder.get("trackingNumber"),
                    "labelId": suborder.get("labelId"),
                    "deliveryExternalId": suborder.get("deliveryExternalId"),
                    "dispatchDate": dispatchDate[:19] if dispatchDate else None,
                    "arrivalDate": arrivalDate[:19] if arrivalDate else None,
                    "arrivalDateEnd": arrivalDateEnd[:19] if arrivalDateEnd else None,
                    "effectiveArrivalDate": effectiveArrivalDate[:19] if effectiveArrivalDate else None,
                    "effectiveDispatchDate": effectiveDispatchDate[:19] if effectiveDispatchDate else None,
                    "effectiveManifestDate": effectiveManifestDate[:19] if effectiveManifestDate else None,
                    "lastNotificationId": suborder.get("lastNotificationId"),
                    "fulfillment": suborder.get("fulfillment"),
                    "cost": suborder.get("cost"),
                    "updatedAt": updatedAt[:19] if updatedAt else None,
                    "summaryId": suborder.get("summaryId"),
                    "facilityConfigId": suborder.get("facilityConfigId"),
                    "bocbolOrderId": suborder.get("bocbolOrderId"),
                    "isSplitted": suborder.get("isSplitted"),
                    "originOrderNumber": suborder.get("originOrderNumber"),
                    "originInvoiceType": suborder.get("originInvoiceType"),
                    "originOrderDate": originOrderDate[:19] if originOrderDate else None,
                    "origin": suborder.get("origin"),
                    "deliveryOptionId": deliveryOption.get("id"),
                    "deliveryOptionName": deliveryOption.get("name"),
                    "deliveryOptionDescription": deliveryOption.get("description"),
                    "deliveryOptionTranslate": deliveryOption.get("translate"),
                    "statusName": status.get("name"),
                    "statusDescription": status.get("description"),
                    "statusTranslate": status.get("translate"),
                    "statusCancelable": status.get("cancelable"),
                    "orderTypeId": suborder.get("id"),
                }
                sub_order_data.append(suborder_info)

                for item in items:
                    status = item.get("status") or {}
                    categoryObj = item.get("categoryObj") or {}
                    item_info = {
                        "id": item.get("id"),
                        "sku": item.get("sku"),
                        "name": item.get("name"),
                        "sellerId": item.get("sellerId"),
                        "jdaSku": item.get("jdaSku"),
                        "basePrice": item.get("basePrice"),
                        "grossPrice": item.get("grossPrice"),
                        "priceAfterDiscounts": item.get("priceAfterDiscounts"),
                        "taxRate": item.get("taxRate"),
                        "size": item.get("size"),
                        "sellerSku": item.get("sellerSku"),
                        "tax": item.get("tax"),
                        "position": item.get("position"),
                        "taxBasis": item.get("taxBasis"),
                        "commission": item.get("commission"),
                        "subOrderNumber": item.get("subOrderNumber"),
                        "reconditioned": item.get("reconditioned"),
                        "cancellationReasonId": item.get("cancellationReasonId"),
                        "statusId": item.get("statusId"),
                        "imagePath": item.get("imagePath"),
                        "itemSize": item.get("itemSize"),
                        "returnId": item.get("returnId"),
                        "userId": item.get("userId"),
                        "shippingCost": item.get("shippingCost"),
                        "externalCategoryId": item.get("externalCategoryId"),
                        "statusName": status.get("name"),
                        "statusDescription": status.get("description"),
                        "statusTranslate": status.get("translate"),
                        "statusCancelable": status.get("cancelable"),
                        "cancellationReason": item.get("cancellationReason"),
                        "return": item.get("return"),
                        "categoryObjId": categoryObj.get("id"),
                        "categoryObjName": categoryObj.get("name"),
                        "categoryObjCode": categoryObj.get("code"),
                        "categoryObjWeight": categoryObj.get("weight"),
                        "categoryObjExternalCategoryId": categoryObj.get("externalCategoryId"),
                        "orderId": item.get("orderId"),
                    }
                    items_data.append(item_info)
        return {
            "orderData": order_data,
            "subOrderData": sub_order_data,
            "itemsData": items_data,
        }

    async def save(self, data: dict):
        if not data:
            return
        order_data = data.get("orderData") or []
        sub_order_data = data.get("subOrderData") or []
        items_data = data.get("itemsData") or []

        await DBManager.upsert("", order_data, ["orderId"])
        subOrderNumbers = [item["subOrderNumber"] for item in order_data]
        placeholders = ",".join(["%s"] * len(subOrderNumbers))
        id_map = {item["subOrderNumber"]: item["id"]
            for item in await DBManager.select(
                f"SELECT id, subOrderNumber FROM paris_order WHERE orderId IN ({placeholders})",
                subOrderNumbers)
        }

        for item in sub_order_data:
            item["main_id"] = id_map.get(item["subOrderNumber"])

        for item in items_data:
            item["main_id"] = id_map.get(item["subOrderNumber"])

        await DBManager.upsert("", sub_order_data, ["id"])
        await DBManager.upsert("", items_data, ["id"])

    async def sync(self, search: dict):

        datatype = search.get("datatype")
        at_str = search.pop("at") if search.get("at") is not None else None
        to_str = search.pop("to") if search.get("to") is not None else None
        at = datetime.strptime(at_str, "%Y-%m-%d") if at_str else (datetime.now() - timedelta(days=1)).date()
        to = datetime.strptime(to_str, "%Y-%m-%d") if to_str else datetime.now().date()

        while at < to:
            if datatype is not None:
                search.pop("datatype")
                if datatype == 0:
                    search["gteUpdatedAt"] = at.isoformat()
                    at += timedelta(days=1)
                    search["lteUpdatedAt"] = at.isoformat()
                elif datatype == 1:
                    search["gteCreatedAt"] = at.isoformat()
                    at += timedelta(days=1)
                    search["lteCreatedAt"] = at.isoformat()
                elif datatype == 2:
                    search["gteCreatedAtInOrigin"] = at.isoformat()
                    at += timedelta(days=1)
                    search["lteCreatedAtInOrigin"] = at.isoformat()

            limit = 100
            offset = 0
            count = 0
            first = True

            while first or (count - offset) < limit:
                search["limit"] = limit
                search["offset"] = offset

                resp = await self.shop.fetch(
                    client=self.client, method="GET", url="/v1/orders", params=search
                )
                if first:
                    first = False
                    count = int(resp.get("count", 0)) or 0
                    if count == 0:
                        break
                if resp:
                    offset += limit
                    resp = self.parse(resp) or {}
                    await self.save(resp)

    async def searchorder(self, search: dict):
        datatype = search.get("datatype")
        at_str = search.pop("at") or None if search.get("at") is not None else None
        to_str = search.pop("to") or None if search.get("to") is not None else None
        at = datetime.strptime(at_str, "%Y-%m-%d") if at_str else (datetime.now() - timedelta(days=1)).date() )
        to = datetime.strptime(to_str, "%Y-%m-%d") if to_str else  datetime.now().date()
        if datatype is None:
            pass
        else:
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
        resp = await self.shop.fetch(
            client=self.client, method="GET", url="/v1/orders", params=search
        )
        return resp
