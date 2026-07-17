"""Falabella 订单资源: 请求 / 解析 / 存储 / 同步"""
import json
from app.db.manager import DBManager
from datetime import datetime, timedelta
from app.platform.FalabellaShop import FalabellaShop
from typing import Dict
from zoneinfo import ZoneInfo
from app.core.converters import _sdec,_sstr

class Order:
    """订单资源"""

    def __init__(self, shop: FalabellaShop):
        self.shop = shop

    def parse_items(self, resp: Dict):

        if not resp:
            return []

        Body = resp.get("SuccessResponse",{}).get("Body") or {}
        # 批量 or 单独
        data = Body.get("Orders",{}).get("Order")

        if not data:
            return []
        else:
            if isinstance(data, Dict):
                data = [data]
            result = []
            SELLER_ID = self.shop.seller_id
            for item in data:
                orderitem = item.get("OrderItems",{}).get("OrderItem") or []
                if orderitem:
                    if isinstance(orderitem, Dict):
                        orderitem = [orderitem]
                    for cur_item in orderitem:
                        cur_item["SellerId"]                    = SELLER_ID
                        ExtraAttributes                         = cur_item.pop("ExtraAttributes", "{}")
                        ExtraAttributes                         = json.loads(ExtraAttributes)
                        cur_item["itemId"]                      = ExtraAttributes.get("itemId")
                        cur_item["originNode"]                  = ExtraAttributes.get("originNode")
                        cur_item["originNodeType"]              = ExtraAttributes.get("originNodeType")
                        cur_item["deliveryOrderGroupId"]        = ExtraAttributes.get("deliveryOrderGroupId")
                        result.append(cur_item)
            return result

    def parse_order(self, resp: Dict):
        """解析订单响应。"""
        if not resp:
            return {}

        SuccessResponse = resp.get("SuccessResponse") or {}

        data = ((SuccessResponse.get("Body") or {}).get("Orders") or {}).get("Order") or []

        if not data:
            return {}
        else:
            order_list                  = []
            addressbilling_list         = []
            addressshipping_list        = []
            extrabillingattributes_list = []
            extraattributes_list        = []
            if isinstance(data, dict):
                data = [data]
            seller_id = self.shop.seller_id
            for Order in data:
                AddressBilling          = {**(Order.get("AddressBilling") or {})}
                AddressShipping         = {**(Order.get("AddressShipping") or {})}
                ExtraBillingAttributes  = {**(Order.get("ExtraBillingAttributes") or {})}
                ExtraAttributes         = {**json.loads(Order.get("ExtraAttributes") or "{}")}

                OrderId                 = int(Order.get("OrderId") or 0)
                order_info = {
                    "SellerId":                     seller_id,
                    "OrderId":                      OrderId,
                    "CustomerFirstName":            Order.get("CustomerFirstName"),
                    "CustomerLastName":             Order.get("CustomerLastName"),
                    "OrderNumber":                  Order.get("OrderNumber"),
                    "PaymentMethod":                Order.get("PaymentMethod"),
                    "Remarks":                      Order.get("Remarks"),
                    "ManifestId":                   Order.get("ManifestId"),
                    "DeliveryInfo":                 Order.get("DeliveryInfo"),
                    "Price":                        _sdec(Order.get("Price")),
                    "GiftOption":                   Order.get("GiftOption"),
                    "GiftMessage":                  Order.get("GiftMessage"),
                    "VoucherCode":                  Order.get("VoucherCode"),
                    "CreatedAt":                    Order.get("CreatedAt") or None,
                    "UpdatedAt":                    Order.get("UpdatedAt") or None,
                    "AddressUpdatedAt":             Order.get("AddressUpdatedAt") or None,
                    "NationalRegistrationNumber":   Order.get("NationalRegistrationNumber"),
                    "ItemsCount":                   int(Order.get("ItemsCount") or 0),
                    "PromisedShippingTime":         Order.get("PromisedShippingTime") or None,
                    "InvoiceRequired":              Order.get("InvoiceRequired"),
                    "OperatorCode":                 Order.get("OperatorCode"),
                    "ShippingType":                 Order.get("ShippingType"),
                    "GrandTotal":                   _sdec(Order.get("GrandTotal")),
                    "ProductTotal":                 _sdec(Order.get("ProductTotal")),
                    "TaxAmount":                    _sdec(Order.get("TaxAmount")),
                    "ShippingFeeTotal":             _sdec(Order.get("ShippingFeeTotal")),
                    "ShippingTax":                  _sdec(Order.get("ShippingTax")),
                    "Voucher":                      Order.get("Voucher"),
                    "Status":                       (Order.get("Statuses") or {}).get("Status"),
                }
                addressbilling_info = {
                    "OrderId":          OrderId,
                    "FirstName":        AddressBilling.get("FirstName"),
                    "LastName":         AddressBilling.get("LastName"),
                    "Address1":         AddressBilling.get("Address1"),
                    "Address3":         AddressBilling.get("Address3"),
                    "Address4":         AddressBilling.get("Address4"),
                    "Address5":         AddressBilling.get("Address5"),
                    "CustomerEmail":    AddressBilling.get("CustomerEmail"),
                    "City":             AddressBilling.get("City"),
                    "Ward":             AddressBilling.get("Ward"),
                    "Region":           AddressBilling.get("Region"),
                    "PostCode":         AddressBilling.get("PostCode"),
                    "Country":          AddressBilling.get("Country"),
                    "Phone":            AddressBilling.get("Phone"),
                    "Phone2":           AddressBilling.get("Phone2"),
                }
                addressshipping_info = {
                    "OrderId":          OrderId,
                    "FirstName":        AddressShipping.get("FirstName"),
                    "LastName":         AddressShipping.get("LastName"),
                    "Phone":            AddressShipping.get("Phone"),
                    "Phone2":           AddressShipping.get("Phone2"),
                    "Address1":         AddressShipping.get("Address1"),
                    "Address2":         AddressShipping.get("Address2"),
                    "Address3":         AddressShipping.get("Address3"),
                    "Address4":         AddressShipping.get("Address4"),
                    "Address5":         AddressShipping.get("Address5"),
                    "CustomerEmail":    AddressShipping.get("CustomerEmail"),
                    "City":             AddressShipping.get("City"),
                    "Ward":             AddressShipping.get("Ward"),
                    "Region":           AddressShipping.get("Region"),
                    "PostCode":         AddressShipping.get("PostCode"),
                    "Country":          AddressShipping.get("Country"),
                    "Latitude":         AddressShipping.get("Latitude"),
                    "Longitude":        AddressShipping.get("Longitude"),
                }
                extrabillingattributes_info = {
                    "OrderId":                  OrderId,
                    "LegalId":                  ExtraBillingAttributes.get("LegalId"),
                    "FiscalPerson":             ExtraBillingAttributes.get("FiscalPerson"),
                    "DocumentType":             ExtraBillingAttributes.get("DocumentType"),
                    "ReceiverRegion":           ExtraBillingAttributes.get("ReceiverRegion"),
                    "ReceiverAddress":          ExtraBillingAttributes.get("ReceiverAddress"),
                    "ReceiverPostcode":         ExtraBillingAttributes.get("ReceiverPostcode"),
                    "ReceiverLegalName":        ExtraBillingAttributes.get("ReceiverLegalName"),
                    "ReceiverMunicipality":     ExtraBillingAttributes.get("ReceiverMunicipality"),
                    "ReceiverTypeRegimen":      ExtraBillingAttributes.get("ReceiverTypeRegimen"),
                    "CustomerVerifierDigit":    ExtraBillingAttributes.get("CustomerVerifierDigit"),
                    "ReceiverPhonenumber":      ExtraBillingAttributes.get("ReceiverPhonenumber"),
                    "ReceiverEmail":            ExtraBillingAttributes.get("ReceiverEmail"),
                    "ReceiverLocality":         ExtraBillingAttributes.get("ReceiverLocality"),
                }
                extraattributes_info = {
                    "OrderId":                      OrderId,
                    "ItemId":                       ExtraAttributes.get("itemId"),
                    "DeliveryOrderGroupId":         ExtraAttributes.get("deliveryOrderGroupId"),
                    "OriginNode":                   ExtraAttributes.get("originNode"),
                    "OriginNodeType":               ExtraAttributes.get("originNodeType"),
                    "CityPoliticalAreaCode":        ExtraAttributes.get("cityPoliticalAreaCode"),
                    "StatePoliticalAreaCode":       ExtraAttributes.get("statePoliticalAreaCode"),
                    "CountryPoliticalAreaCode":     ExtraAttributes.get("countryPoliticalAreaCode"),
                    "MunicipalPoliticalAreaCode":   ExtraAttributes.get("municipalPoliticalAreaCode"),
                }
                order_list.append(order_info)
                addressbilling_list.append(addressbilling_info)
                addressshipping_list.append(addressshipping_info)
                extrabillingattributes_list.append(extrabillingattributes_info)
                extraattributes_list.append(extraattributes_info)
            return {
                "order_rows": order_list,
                "addressbilling_rows": addressbilling_list,
                "addressshipping_rows": addressshipping_list,
                "extrabillingattributes_rows": extrabillingattributes_list,
                "extraattributes_rows": extraattributes_list,
            }

    def _build_search(self, search: Dict):

        datatype = search.get("datatype")
        at = search.get("at")
        to = search.get("to")

        params = {k: v for k, v in search.items() if k not in ("at", "to", "datatype")}

        if datatype is not None:

            params_list = []

            date_fields = {
                0: ("UpdatedAfter", "UpdatedBefore"),
                1: ("CreatedAfter", "CreatedBefore"),
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
                    params[gte_key] = current_at.strftime("%Y-%m-%dT%H:%M:%S")
                    params[lte_key] = current_to.strftime("%Y-%m-%dT%H:%M:%S")
                    params_list.append(params.copy())
                    current_at += timedelta(days=1)

                return params_list
            else:
                tz_str = self.shop.timezone
                tz_now = datetime.now(tz=ZoneInfo(tz_str))
                at = tz_now - timedelta(hours=1)
                to = tz_now
                params[gte_key] = at.strftime("%Y-%m-%dT%H:%M:%S")
                params[lte_key] = to.strftime("%Y-%m-%dT%H:%M:%S")
                params_list.append(params.copy())
                return params_list
        else:
            return [params]

    async def get_orders(self, search: Dict):

        resp = self.shop.request(
            method="GET",
            action="GetOrders",
            params=search,
        )
        return resp

    async def get_order(self, order_id: str):

        resp = self.shop.request(
            method="GET",
            action="GetOrder",
            params={"OrderId": order_id},
        )
        return resp

    async def get_items(self, order_ids: str):

        resp = self.shop.request(
            method="GET",
            action="GetMultipleOrderItems",
            params={"OrderIdList": order_ids},
        )
        return resp

    async def get_item(self, order_id: str):

        resp = self.shop.request(
            method="GET",
            action="GetOrderItems",
            params={"OrderId": order_id},
        )
        return resp

    async def save_order(self, data: Dict):

        if not data:
            return

        order_info                  = data.get("order_rows") or []
        addressbilling_info         = data.get("addressbilling_rows") or []
        addressshipping_info        = data.get("addressshipping_rows") or []
        extrabillingattributes_info = data.get("extrabillingattributes_rows") or []
        extraattributes_info        = data.get("extraattributes_rows") or []

        await DBManager.upsert("falabella_orders", order_info, ["SellerId", "OrderId"])

        ids = [item["OrderId"] for item in order_info]
        placeholders = ",".join(["%s"] * len(ids))
        id_map = {
            item["OrderId"]: item["ID"]
            for item in await DBManager.select(
                f"SELECT ID,OrderId FROM falabella_orders WHERE SellerID = %s AND OrderID IN ({placeholders})",[self.shop.seller_id] + ids,
            )
        }

        for item in addressbilling_info:
            item["RBOrderId"] = id_map.get(item["OrderId"])
            item.pop("OrderId")
        await DBManager.upsert(
            "falabella_order_address_billing", addressbilling_info, ["RBOrderId"]
        )

        for item in addressshipping_info:
            item["RBOrderId"] = id_map.get(item["OrderId"])
            item.pop("OrderId")
        await DBManager.upsert(
            "falabella_order_address_shipping", addressshipping_info, ["RBOrderId"]
        )

        for item in extrabillingattributes_info:
            item["RBOrderId"] = id_map.get(item["OrderId"])
            item.pop("OrderId")
        await DBManager.upsert(
            "falabella_order_extra_billing_attributes",extrabillingattributes_info,["RBOrderId"],
        )

        for item in extraattributes_info:
            item["RBOrderId"] = id_map.get(item["OrderId"])
            item.pop("OrderId")
        await DBManager.upsert(
            "falabella_order_extra_attributes", extraattributes_info, ["RBOrderId"]
        )

        return id_map

    async def save_item(self, data: Dict):
        await DBManager.upsert("falabella_order_items", data, ["OrdersId", "OrderItemId"])

    async def sync_order(self, search: Dict):
        """全量同步商品 (自动翻页)。返回同步总数。"""

        for params in self._build_search(search):

            limit   = params.get("Limit", 100)
            offset  = params.get("Offset", 0)
            total   = None

            while total is None or offset < total:
                params.update({"Limit": limit, "Offset": offset})

                resp = await self.get_orders(params)
                SuccessResponse = resp.get("SuccessResponse") or {}
                if total is None:
                    total = int((SuccessResponse.get("Head") or {}).get("TotalCount", 0)) or 0
                    if total == 0:
                        break
                if resp:
                    offset      += limit
                    resp         = self.parse_order(resp)
                    id_map       = await self.save_order(resp) or {}
                    orderids     = "["+_sstr(id_map.keys())+"]"
                    if orderids:
                        item_resp     = await self.get_items(orderids)
                        if item_resp:
                            item_resp = self.parse_items(item_resp)
                            for i in item_resp:
                                i["RBOrderId"] = id_map.get(int(i.get("OrderId")))
                            await DBManager.upsert("falabella_order_items", item_resp, ["OrdersId", "OrderItemId"])
