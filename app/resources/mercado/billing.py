"""
Mercado billing资源:请求/解析/存储/同步。
"""
import asyncio
from app.db.manager import DBManager
from datetime import timedelta
from app.platform.MercadoShop import MercadoShop
from typing import Dict, List
from app.core.converters import _trim, _json, _str


class Billing:
    """billing资源。"""

    def __init__(self, shop: MercadoShop):
        self.shop = shop

    def parse_periods(self, resp: dict):
        if not resp:
            return []

        seller_id = self.shop.seller_id
        results = resp.get("results") or []
        period_rows = []
        for item in results:
            period_rows.append({
                "seller_id":                                        seller_id,
                "group_id":                                         item.get('group_id'),
                "amount":                                           item.get('amount'),
                "unpaid_amount":                                    item.get('unpaid_amount'),
                "date_from":                                        item.get('date_from'),
                "date_to":                                          item.get('date_to'),
                "period_key":                                       item.get('key'),
                "expiration_date":                                  item.get('expiration_date'),
                "debt_expiration_date":                             item.get('debt_expiration_date'),
                "debt_expiration_date_move_reason":                 item.get('debt_expiration_date_move_reason'),
                "debt_expiration_date_move_reason_description":     item.get('debt_expiration_date_move_reason_description'),
                "period_status":                                    item.get('period_status'),
            })
        return period_rows


    def parse_ml_billing(self, results: List,key: str):
        if not results:
            return []

        seller_id = self.shop.seller_id
        billing_rows = []
        for item in results:
            key =                   item.get('key')
            charge_info =           item.get('charge_info') or {}
            discount_info =         item.get('discount_info') or {}
            sales_info =            item.get('sales_info')[0] if item.get('sales_info') else {}
            shipping_info =         item.get('shipping_info') or {}
            items_info =            item.get('items_info')[0] if item.get('items_info') else {}
            document_info =         item.get('document_info') or {}
            marketplace_info =      item.get('marketplace_info') or {}
            currency_info =         item.get('currency_info') or {}
            main_dict = {
                    "seller_id":                            seller_id,
                    "key_id":                               key,
                    "currency_id":                          currency_info.get('currency_id'),
                    "marketplace":                          marketplace_info.get('marketplace'),
                    "document_id":                          document_info.get('document_id'),
                    "shipping_id":                          shipping_info.get('shipping_id'),
                    "pack_id":                              shipping_info.get('pack_id'),
                    "receiver_shipping_cost":               shipping_info.get('receiver_shipping_cost'),
                    "charge_amount_without_discount":       discount_info.get('charge_amount_without_discount'),
                    "discount_amount":                      discount_info.get('discount_amount'),
                    "discount_reason":                      discount_info.get('discount_reason'),
                    "rebate":                               discount_info.get('rebate'),
                    "legal_document_number":                charge_info.get('legal_document_number'),
                    "legal_document_status":                charge_info.get('legal_document_status'),
                    "legal_document_status_description":    charge_info.get('legal_document_status_description'),
                    "creation_date_time":                   charge_info.get('creation_date_time'),
                    "detail_id":                            charge_info.get('detail_id'),
                    "transaction_detail":                   charge_info.get('transaction_detail'),
                    "debited_from_operation":               charge_info.get('debited_from_operation'),
                    "debited_from_operation_description":   charge_info.get('debited_from_operation_description'),
                    "status":                               charge_info.get('status'),
                    "status_description":                   charge_info.get('status_description'),
                    "charge_bonified_id":                   charge_info.get('charge_bonified_id'),
                    "detail_amount":                        charge_info.get('detail_amount'),
                    "detail_type":                          charge_info.get('detail_type'),
                    "detail_sub_type":                      charge_info.get('detail_sub_type')
            }
            main_dict.update({
                "order_id":             sales_info.get('order_id'),
                "operation_id":         sales_info.get('operation_id'),
                "sale_date_time":       sales_info.get('sale_date_time'),
                "sales_channel":        sales_info.get('sales_channel'),
                "payer_nickname":       sales_info.get('payer_nickname'),
                "state_name":           sales_info.get('state_name'),
                "transaction_amount":   sales_info.get('transaction_amount'),
                "wholesale_price":      sales_info.get('wholesale_price')
            })
            main_dict.update({
                "item_id":          items_info.get('item_id'),
                "item_title":       items_info.get('item_title'),
                "item_type":        items_info.get('item_type'),
                "item_category":    items_info.get('item_category'),
                "inventory_id":     items_info.get('inventory_id'),
                "item_amount":      items_info.get('item_amount'),
                "item_price":       items_info.get('item_price'),
            })
            billing_rows.append(main_dict)

        return billing_rows


    def parse_mp_billing(self, results: List, key: str):
        if not results:
            return []
        seller_id = self.shop.seller_id
        billing_rows = []
        for item in results:
            charge_info             = item.get('charge_info') or {}
            operation_info          = item.get('operation_info') or {}
            perception_info         = item.get('perception_info') or {}
            document_info           = item.get('document_info') or {}
            marketplace_info        = item.get('marketplace_info') or {}
            currency_info           = item.get('currency_info') or {}
            main_dict = {
                "seller_id":                            seller_id,
                "key_id":                               key,
                "currency_id":                          currency_info.get('currency_id'),
                "marketplace":                          marketplace_info.get('marketplace'),
                "document_id":                          document_info.get('document_id'),
                "legal_document_number":                charge_info.get('legal_document_number'),
                "legal_document_status":                charge_info.get('legal_document_status'),
                "legal_document_status_description":    charge_info.get('legal_document_status_description'),
                "detail_id":                            charge_info.get('detail_id'),
                "movement_id":                          charge_info.get('movement_id'),
                "transaction_detail":                   charge_info.get('transaction_detail'),
                "debited_from_operation":               charge_info.get('debited_from_operation'),
                "debited_from_operation_description":   charge_info.get('debited_from_operation_description'),
                "status":                               charge_info.get('status'),
                "status_description":                   charge_info.get('status_description'),
                "charge_bonified_id":                   charge_info.get('charge_bonified_id'),
                "creation_date_time":                   charge_info.get('creation_date_time'),
                "detail_amount":                        charge_info.get('detail_amount'),
                "detail_type":                          charge_info.get('detail_type'),
                "detail_sub_type":                      charge_info.get('detail_sub_type'),
                "operation_type":                       operation_info.get('operation_type'),
                "operation_type_description":           operation_info.get('operation_type_description'),
                "reference_id":                         operation_info.get('reference_id'),
                "sales_channel":                        operation_info.get('sales_channel'),
                "store_id":                             operation_info.get('store_id'),
                "store_name":                           operation_info.get('store_name'),
                "external_reference":                   operation_info.get('external_reference'),
                "payer_nickname":                       operation_info.get('payer_nickname'),
                "transaction_amount":                   operation_info.get('transaction_amount'),
                "aliquot":                              perception_info.get('aliquot'),
                "taxable_amount":                       perception_info.get('taxable_amount'),
            }

            billing_rows.append(main_dict)

        return billing_rows


    def parse_flex_billing(self, results: List, key: str):
        if not results:
            return []

        billing_rows = []
        seller_id = self.shop.seller_id
        for item in results:
            charge_info     = item.get('charge_info') or {}
            shipping_info   = item.get('shipping_info') or {}
            document_info   = item.get('document_info') or {}
            order           = shipping_info.get('order') or {}
            main_dict = {
                    "seller_id":                                seller_id,
                    "key_id":                                   key,
                    "document_id":                              document_info.get('document_id'),
                    "legal_document_number":                    charge_info.get('legal_document_number'),
                    "legal_document_status":                    charge_info.get('legal_document_status'),
                    "legal_document_status_description":        charge_info.get('legal_document_status_description'),
                    "creation_date_time":                       charge_info.get('creation_date_time'),
                    "detail_id":                                charge_info.get('detail_id'),
                    "detail_associated_id":                     charge_info.get('detail_associated_id'),
                    "detail_amount":                            charge_info.get('detail_amount'),
                    "transaction_detail":                       charge_info.get('transaction_detail'),
                    "detail_type":                              charge_info.get('detail_type'),
                    "detail_sub_type":                          charge_info.get('detail_sub_type'),
                    "concept_type":                             charge_info.get('concept_type'),
                    "shipping_id":                              shipping_info.get('shipping_id'),
                    "receiver_nickname":                        shipping_info.get('receiver_nickname'),
                    "pack_id":                                  shipping_info.get('pack_id'),
                    "receiver_shipping_cost":                   shipping_info.get('receiver_shipping_cost'),
                    "order_id":                                 order.get('order_id'),
                    "date_created":                             order.get('date_created'),
                    "total_amount":                             order.get('total_amount'),
                    "payment_id":                               order.get('payment_id'),
                    "buyer_nickname":                           order.get('buyer_nickname')
            }

            billing_rows.append(main_dict)

        return billing_rows


    def parse_full_billing(self, results: List, key: str):
        if not results:
            return []

        billing_rows = []
        seller_id = self.shop.seller_id
        for item in results:
            charge_info         = item.get('charge_info') or {}
            fulfillment_info    = item.get('fulfillment_info') or {}
            document_info       = item.get('document_info') or {}

            main_dict = {
                    "seller_id":                            seller_id,
                    "key":                                  key,
                    "document_id":                          document_info.get('document_id'),
                    "legal_document_number":                charge_info.get('legal_document_number'),
                    "legal_document_status":                charge_info.get('legal_document_status'),
                    "legal_document_status_description":    charge_info.get('legal_document_status_description'),
                    "creation_date_time":                   charge_info.get('creation_date_time'),
                    "detail_id":                            charge_info.get('detail_id'),
                    "detail_amount":                        charge_info.get('detail_amount'),
                    "transaction_detail":                   charge_info.get('transaction_detail'),
                    "charge_bonified_id":                   charge_info.get('charge_bonified_id'),
                    "detail_type":                          charge_info.get('detail_type'),
                    "detail_sub_type":                      charge_info.get('detail_sub_type'),
                    "concept_type":                         charge_info.get('concept_type'),
                    "payment_id":                           fulfillment_info.get('payment_id'),
                    "type":                                 fulfillment_info.get('type'),
                    "amount_per_unit":                      fulfillment_info.get('amount_per_unit'),
                    "amount":                               fulfillment_info.get('amount'),
                    "sku":                                  fulfillment_info.get('sku'),
                    "ean":                                  fulfillment_info.get('ean'),
                    "item_id":                              fulfillment_info.get('item_id'),
                    "item_title":                           fulfillment_info.get('item_title'),
                    "variation":                            fulfillment_info.get('variation'),
                    "quantity":                             fulfillment_info.get('quantity'),
                    "volume_type":                          fulfillment_info.get('volume_type'),
                    "inventory_id":                         fulfillment_info.get('inventory_id'),
                    "warehouse_id":                         fulfillment_info.get('warehouse_id'),
                    "source_id":                            fulfillment_info.get('source_id'),
                    "item_quantity":                        fulfillment_info.get('item_quantity')
            }

            billing_rows.append(main_dict)

        return billing_rows


    async def Periods(self,group: str|None = None,document_type: str|None = None,offset: int = 0,limit: int = 12):

        resp = await self.shop.request(
            method="GET",
            url=f"/billing/integration/monthly/periods?group={group}&document_type={document_type}&offset={offset}&limit={limit}",
            headers={
                "Content-Type": "application/json",
            }
        )

        return resp


    async def Billing(self, key: str|None = None, group: str|None = None, document_type: str|None = None, limit: int|None = 1000, from_id: int|None = 0):

        if group == "ML":
            url = f"/billing/integration/periods/key/{key}/group/ML/details?document_type={document_type}&limit={limit}&from_id={from_id}&sort_by=DATE&order_by=ASC"
        elif group == "MP":
            url = f"/billing/integration/periods/key/{key}/group/MP/details?document_type={document_type}&limit={limit}&from_id={from_id}&sort_by=DATE&order_by=ASC"
        elif group == "FLEX":
            url = f"/billing/integration/periods/key/{key}/group/ML/flex/details?document_type={document_type}&limit={limit}&from_id={from_id}&sort_by=DATE&order_by=ASC"
        elif group == "FULL":
            url = f"/billing/integration/periods/key/{key}/group/ML/full/details?document_type={document_type}&limit={limit}&from_id={from_id}&sort_by=DATE&order_by=ASC"
        else:
            return {}

        resp = await self.shop.request(
            method="GET",
            url= url,
            headers={
                "Content-Type": "application/json",
            }
        )

        return resp


    async def sync_billing(self, ):
        pass
