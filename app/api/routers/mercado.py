"""
Mercado Libre 路由: 商品/变体/订单/货运/库存/评价/账单/广告 共 7 个资源。

路由结构:
  GET /mercado/ads/advertisers/sync                                — 全量同步广告主
  GET /mercado/ads/advertisers/search                              — 搜索广告主
  GET /mercado/ads/adgroups/sync                                   — 全量同步广告组
  GET /mercado/ads/adgroups/search                                 — 搜索广告组
  GET /mercado/ads/adgroups/details/sync                           — 全量同步广告组详情
  GET /mercado/ads/adgroup/details/search                          — 搜索广告组详情
  GET /mercado/order/sync                                          — 全量同步订单
  GET /mercado/order/search                                        — 搜索订单
  GET /mercado/order/{order_id}                                    — 获取单个订单
  GET /mercado/shipment/{shipment_id}                              — 获取货运详情
  GET /mercado/shipment/{shipment_id}/history                      — 获取货运历史
  GET /mercado/shipment/{shipment_id}/sla                          — 获取货运SLA
  GET /mercado/payment/{payment_id}                                — 获取支付详情

"""
# package
# import json
import traceback
from aiolimiter import AsyncLimiter

# fastapi
from fastapi import APIRouter, HTTPException, Query, Request, Depends

# basemodel
from app.api.schemas import ApiResponse, MLOrderSearch

# 资源
from app.resources.mercado.advertise import Advertise
from app.resources.mercado.product import Product
from app.resources.mercado.billing import Billing
from app.resources.mercado.order import Order
from app.resources.mercado.stock import Stock



router = APIRouter()
def get_shops(request: Request):
    return request.app.state.mercado_shops


# ═════════════════════════════════════════════════════════
# Advertise
# ═════════════════════════════════════════════════════════

@router.get("/mercado/ads/advertisers/sync", response_model=ApiResponse)
async def advertise_sync(
    shops           = Depends(get_shops),
    seller_id:  int = Query(None, description="同步指定店铺, 默认None同步所有店铺"),
    PRODUCT_ID: str = Query(),
):
    """全量同步商品: 拉取全部 item_id → 并发查详情 → 解析存储。"""

    targets = [shops.get(seller_id)] if seller_id else shops.values()

    for shop in targets:
        try:
            await Advertise(shop).sync_advertisers(PRODUCT_ID)
        except Exception as e:
            return ApiResponse(
                success=False,
                message=f"sync mercado shop's advertisers failed for shop {shop.seller_id}",
                error = {
                    "type":         type(e).__name__,        # 异常类型
                    "message":      str(e),                  # 异常消息
                    "traceback":    traceback.format_exc(),  # 完整堆栈
                },
            )

    return ApiResponse(success=True, message="sync mercado shop's advertisers done")

@router.get("/mercado/ads/adgroups/sync", response_model=ApiResponse)
async def adgroups_sync(
    shops          = Depends(get_shops),
    seller_id: int = Query(None, description="同步指定店铺, 默认None同步所有店铺"),
):
    if seller_id is not None and seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    targets = [shops.get(seller_id)] if seller_id else shops.values()

    for shop in targets:
        try:
            await Advertise(shop).sync_adgroups()
        except Exception as e:
            return ApiResponse(
                success=False,
                message=f"sync Mercado adgroups failed for shop {shop.seller_id}",
                error = {
                    "type":         type(e).__name__,        # 异常类型
                    "message":      str(e),                  # 异常消息
                    "traceback":    traceback.format_exc(),  # 完整堆栈
                },
            )

    return ApiResponse(
        success=True,
        message="successfully get Mercado adgroups",
    )

@router.get("/mercado/ads/adgroups/details/sync", response_model=ApiResponse)
async def adgroups_details_sync(
    shops         = Depends(get_shops),
    seller_id:int = Query(None, description="同步指定店铺, 默认None同步所有店铺"),
    data_at:  str = Query(None, description="开始日期 YYYY-MM-DD"),
    data_to:  str = Query(None, description="结束日期 YYYY-MM-DD"),
):
    if seller_id is not None and seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    targets = [shops.get(seller_id)] if seller_id else shops.values()

    for shop in targets:
        try:
            await Advertise(shop).sync_adgroup_details(data_at, data_to)
        except Exception as e:
            return ApiResponse(
                success=False,
                message=f"sync Mercado adgroups details failed for shop {shop.seller_id}",
                error = {
                    "type":         type(e).__name__,        # 异常类型
                    "message":      str(e),                  # 异常消息
                    "traceback":    traceback.format_exc(),  # 完整堆栈
                },
            )

    return ApiResponse(
        success=True,
        message="successfully sync Mercado adgroups details",
    )

@router.get("/mercado/ads/advertisers/search", response_model=ApiResponse)
async def advertise_search(
    shops           =Depends(get_shops),
    seller_id:  int = Query(),
    product_id: str = Query(),
):
    if seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    shop = shops[seller_id]

    try:
        resp = await Advertise(shop).get_advertisers(product_id)
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"search Mercado advertisers failed for shop {seller_id}",
            error = {
                "type":         type(e).__name__,        # 异常类型
                "message":      str(e),                  # 异常消息
                "traceback":    traceback.format_exc(),  # 完整堆栈
            },
        )

    return ApiResponse(
        success=True,
        message="successfully get Mercado advertisers",
        data=resp,
    )

@router.get("/mercado/ads/adgroups/search", response_model=ApiResponse)
async def adgroups_search(
    shops                   = Depends(get_shops),
    seller_id:          int = Query(),
    advertiser_site_id: str = Query(),
    advertiser_id:      str = Query(),
    limit:              int = Query(default=100),
    offset:             int = Query(default=0),
    data_at:            str = Query(),
    data_to:            str = Query(),
):
    if seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    shop = shops[seller_id]

    try:
        resp = await Advertise(shop).get_adgroups(advertiser_site_id, advertiser_id, limit, offset, data_at, data_to)
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"search Mercado adgroups failed for shop {seller_id}",
            error = {
                "type":         type(e).__name__,        # 异常类型
                "message":      str(e),                  # 异常消息
                "traceback":    traceback.format_exc(),  # 完整堆栈
            },
        )

    return ApiResponse(
        success=True,
        message="successfully get Mercado adgroups",
        data=resp,
    )

@router.get("/mercado/ads/adgroup/details/search", response_model=ApiResponse)
async def adgroups_details_search(
    shops                   = Depends(get_shops),
    seller_id:          int = Query(),
    advertiser_site_id: str = Query(),
    ad_group_id:        str = Query(),
    data_at:            str = Query(),
    data_to:            str = Query(),
):
    if seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    shop = shops[seller_id]

    try:
        resp = await Advertise(shop).get_adgroup_details(advertiser_site_id, ad_group_id, data_at, data_to)
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"search Mercado adgroup_details failed for shop {seller_id}",
            error = {
                "type":         type(e).__name__,        # 异常类型
                "message":      str(e),                  # 异常消息
                "traceback":    traceback.format_exc(),  # 完整堆栈
            },
        )

    return ApiResponse(
        success=True,
        message="successfully get Mercado adgroup_details",
        data=resp,
    )

# ═════════════════════════════════════════════════════════
# Pack
# ═════════════════════════════════════════════════════════

@router.get("/mercado/order/pack/{pack_id}", response_model=ApiResponse)
async def pack_get(
    pack_id: str,
    shops           = Depends(get_shops),
    seller_id:  int = Query(),
):
    """获取单个订单详情。"""

    if seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    shop = shops[seller_id]

    try:
        resp = await Order(shop).get_pack(pack_id)
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"get mercado pack failed for shop {seller_id}",
            error = {
                "type":         type(e).__name__,        # 异常类型
                "message":      str(e),                  # 异常消息
                "traceback":    traceback.format_exc(),  # 完整堆栈
            },
        )

    return ApiResponse(
        success=True,
        message="successfully get mercado pack",
        data=resp,
    )

# ═════════════════════════════════════════════════════════
# Order
# ═════════════════════════════════════════════════════════

@router.get("/mercado/order/sync", response_model=ApiResponse)
async def order_sync(
    shops                 = Depends(get_shops),
    seller_id:        int = Query(None, description="同步指定店铺, 默认None同步所有店铺"),
    search: MLOrderSearch = Depends(),
):
    """全量同步订单: 按日期范围分页拉取 → 解析 → 存储订单/商品/支付 → 并发拉取货运详情。"""

    targets = [shops.get(seller_id)] if seller_id in shops else shops.values()

    search_dict = search.model_dump(exclude_none=True)

    for shop in targets:
        try:
            await Order(shop).sync_order(search_dict)
        except Exception as e:
            return ApiResponse(
                success=False,
                message=f"sync mercado orders failed for shop {shop.seller_id}",
                error = {
                    "type":         type(e).__name__,        # 异常类型
                    "message":      str(e),                  # 异常消息
                    "traceback":    traceback.format_exc(),  # 完整堆栈
                },
            )

    return ApiResponse(success=True, message="sync mercado orders done")

@router.get("/mercado/order/search", response_model=ApiResponse)
async def order_search(
    shops                 = Depends(get_shops),
    seller_id:        int = Query(),
    search: MLOrderSearch = Depends(),
):
    """搜索订单。"""

    if seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    shop = shops[seller_id]

    search_dict = search.model_dump(exclude_none=True)
    search_dict["seller"] = seller_id

    try:
        resp = await Order(shop).search_order(search_dict)
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"search mercado orders failed for shop {seller_id}",
            error = {
                "type":         type(e).__name__,        # 异常类型
                "message":      str(e),                  # 异常消息
                "traceback":    traceback.format_exc(),  # 完整堆栈
            },
        )

    return ApiResponse(
        success=True,
        message="successfully get mercado orders",
        data=resp,
    )

@router.get("/mercado/order/{order_id}", response_model=ApiResponse)
async def order_get(
    order_id: str,
    shops           = Depends(get_shops),
    seller_id:  int = Query(),
):
    """获取单个订单详情。"""

    if seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    shop = shops[seller_id]

    try:
        resp = await Order(shop).get_order(order_id)
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"get mercado order failed for shop {seller_id}",
            error = {
                "type":         type(e).__name__,        # 异常类型
                "message":      str(e),                  # 异常消息
                "traceback":    traceback.format_exc(),  # 完整堆栈
            },
        )

    return ApiResponse(
        success=True,
        message="successfully get mercado order",
        data=resp,
    )

# ═════════════════════════════════════════════════════════
# Shipment
# ═════════════════════════════════════════════════════════

@router.get("/mercado/shipment/{shipment_id}", response_model=ApiResponse)
async def shipment_get(shipment_id: str, shops = Depends(get_shops), seller_id: int = Query()):
    """获取货运详情。"""

    if seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    shop = shops[seller_id]

    try:
        resp = await Order(shop).get_shipment(shipment_id)
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"get mercado shipment failed for shop {seller_id}",
            error = {
                "type":         type(e).__name__,        # 异常类型
                "message":      str(e),                  # 异常消息
                "traceback":    traceback.format_exc(),  # 完整堆栈
            },
        )

    return ApiResponse(
        success=True,
        message="successfully get mercado shipment",
        data=resp,
    )


@router.get("/mercado/shipment/{shipment_id}/history", response_model=ApiResponse)
async def shipment_history_get(shipment_id: str, shops = Depends(get_shops), seller_id: int = Query()):
    """获取货运历史。"""

    if seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    shop = shops[seller_id]

    try:
        resp = await Order(shop).get_shipment_history(shipment_id)
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"get mercado shipment history failed for shop {seller_id}",
            error = {
                "type":         type(e).__name__,        # 异常类型
                "message":      str(e),                  # 异常消息
                "traceback":    traceback.format_exc(),  # 完整堆栈
            },
        )

    return ApiResponse(
        success=True,
        message="successfully get mercado shipment history",
        data=resp,
    )


@router.get("/mercado/shipment/{shipment_id}/sla", response_model=ApiResponse)
async def shipment_sla_get(shipment_id: str, shops = Depends(get_shops), seller_id: int = Query()):
    """获取货运SLA。"""

    if seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    shop = shops[seller_id]

    try:
        resp = await Order(shop).get_shipment_sla(shipment_id)
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"get mercado shipment sla failed for shop {seller_id}",
            error = {
                "type":         type(e).__name__,        # 异常类型
                "message":      str(e),                  # 异常消息
                "traceback":    traceback.format_exc(),  # 完整堆栈
            },
        )

    return ApiResponse(
        success=True,
        message="successfully get mercado shipment sla",
        data=resp,
    )


# ═════════════════════════════════════════════════════════
# Payment
# ═════════════════════════════════════════════════════════

@router.get("/mercado/payment/{payment_id}", response_model=ApiResponse)
async def payment_get(payment_id: str, shops = Depends(get_shops), seller_id: int = Query()):
    """获取支付详情 → 解析 → 存储。"""

    if seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    shop = shops[seller_id]

    try:
        resp = await Order(shop).get_payment(payment_id)
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"get mercado payment failed for shop {seller_id}",
            error = {
                "type":         type(e).__name__,        # 异常类型
                "message":      str(e),                  # 异常消息
                "traceback":    traceback.format_exc(),  # 完整堆栈
            },
        )

    return ApiResponse(
        success=True,
        message="successfully get mercado payment",
        data=resp,
    )


@router.get("/mercado/discount/{order_id}", response_model=ApiResponse)
async def discount_get(order_id: str, shops = Depends(get_shops), seller_id: int = Query()):
    """获取支付详情 → 解析 → 存储。"""

    if seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    shop = shops[seller_id]

    try:
        resp = await Order(shop).get_discount(order_id)

    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"get mercado discount failed for shop {seller_id}",
            error = {
                "type":         type(e).__name__,        # 异常类型
                "message":      str(e),                  # 异常消息
                "traceback":    traceback.format_exc(),  # 完整堆栈
            },
        )

    return ApiResponse(
        success=True,
        message="successfully get mercado discount",
        data=resp,
    )

# ═════════════════════════════════════════════════════════
# Stock
# ═════════════════════════════════════════════════════════

@router.get("/mercado/stock/user_product/{user_product_id}", response_model=ApiResponse)
async def get_mercado_stock(user_product_id: str, shops = Depends(get_shops), seller_id: int = Query()):
    """获取支付详情 → 解析 → 存储。"""

    if seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    shop = shops[seller_id]

    try:
        resp = await Stock(shop).get_stock(user_product_id)
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"get mercado stock failed for shop {seller_id}",
            error = {
                "type":         type(e).__name__,        # 异常类型
                "message":      str(e),                  # 异常消息
                "traceback":    traceback.format_exc(),  # 完整堆栈
            },
        )

    return ApiResponse(
        success=True,
        message="successfully get mercado stock",
        data=resp,
    )

@router.get("/mercado/stock/inventory/{inventory_id}", response_model=ApiResponse)
async def get_inventories(inventory_id: str, shops = Depends(get_shops), seller_id: int = Query()):
    """获取支付详情 → 解析 → 存储。"""

    if seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    shop = shops[seller_id]

    try:
        resp = await Stock(shop).get_fulfillment_stock(inventory_id)
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"get mercado fulfillment stock failed for shop {seller_id}",
            error = {
                "type":         type(e).__name__,        # 异常类型
                "message":      str(e),                  # 异常消息
                "traceback":    traceback.format_exc(),  # 完整堆栈
            },
        )

    return ApiResponse(
        success=True,
        message="successfully get mercado fulfillment stock",
        data=resp,
    )

@router.get("/mercado/stock/sync/user_product", response_model=ApiResponse)
async def sync_stock(shops = Depends(get_shops), seller_id: int = Query()):
    """获取支付详情 → 解析 → 存储。"""

    targets = [shops.get(seller_id)] if seller_id else shops.values()

    stock_limit = AsyncLimiter(50)

    for shop in targets:
        try:
            await Stock(shop).sync_stock(stock_limit)
        except Exception as e:
            return ApiResponse(
                success=False,
                message=f"get mercado stock failed for shop {seller_id}",
                error = {
                    "type":         type(e).__name__,        # 异常类型
                    "message":      str(e),                  # 异常消息
                    "traceback":    traceback.format_exc(),  # 完整堆栈
                },
            )

    return ApiResponse(
        success=True,
        message="successfully get mercado stock",
    )

# ═════════════════════════════════════════════════════════
# Product
# ═════════════════════════════════════════════════════════

@router.get("/mercado/product/item/{item_id}", response_model=ApiResponse)
async def get_product(item_id: str, shops = Depends(get_shops), seller_id: int = Query()):
    """获取支付详情 → 解析 → 存储。"""

    if seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    shop = shops[seller_id]

    try:
        resp = await Product(shop).get_product(item_id)
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"get mercado product failed for shop {seller_id}",
            error = {
                "type":         type(e).__name__,        # 异常类型
                "message":      str(e),                  # 异常消息
                "traceback":    traceback.format_exc(),  # 完整堆栈
            },
        )

    return ApiResponse(
        success=True,
        message="successfully get mercado product",
        data=resp,
    )

@router.get("/mercado/product/item/{item_id}/variation/{variation_id}", response_model=ApiResponse)
async def get_variation(item_id: str, variation_id: str, shops = Depends(get_shops), seller_id: int = Query()):
    """获取支付详情 → 解析 → 存储。"""

    if seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    shop = shops[seller_id]

    try:
        resp = await Product(shop).get_variation(item_id, variation_id)
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"get mercado variation failed for shop {seller_id}",
            error = {
                "type":         type(e).__name__,        # 异常类型
                "message":      str(e),                  # 异常消息
                "traceback":    traceback.format_exc(),  # 完整堆栈
            },
        )

    return ApiResponse(
        success=True,
        message="successfully get mercado variation",
        data=resp,
    )

@router.get("/mercado/shops/product/sync/", response_model=ApiResponse)
async def sync_product(shops = Depends(get_shops), seller_id: int = Query()):
    """获取支付详情 → 解析 → 存储。"""

    targets = [shops.get(seller_id)] if seller_id else shops.values()

    for shop in targets:
        try:
            await Product(shop).sync_product()
            await Product(shop).sync_variation()
        except Exception as e:
            return ApiResponse(
                success=False,
                message=f"sync mercado product failed for shop {seller_id}",
                error = {
                    "type":         type(e).__name__,        # 异常类型
                    "message":      str(e),                  # 异常消息
                    "traceback":    traceback.format_exc(),  # 完整堆栈
                },
            )

    return ApiResponse(
        success=True,
        message="successfully sync mercado product",
    )

# ═════════════════════════════════════════════════════════
# Billing
# ═════════════════════════════════════════════════════════

@router.get("/mercado/billing/Periods", response_model=ApiResponse)
async def get_Periods(
    shops               = Depends(get_shops),
    seller_id:      int = Query(),
    group:          str = Query(),
    document_type:  str = Query(),
):
    """获取支付详情 → 解析 → 存储。"""

    if seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    shop = shops[seller_id]

    try:
        resp = await Billing(shop).Periods(group=group, document_type=document_type)
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"get mercado billing periods failed for shop {seller_id}",
            error = {
                "type":         type(e).__name__,        # 异常类型
                "message":      str(e),                  # 异常消息
                "traceback":    traceback.format_exc(),  # 完整堆栈
            },
        )

    return ApiResponse(
        success=True,
        message="successfully get mercado billing periods",
        data=resp,
    )

@router.get("/mercado/Periods/billing", response_model=ApiResponse)
async def get_Billing(
    shops               = Depends(get_shops),
    seller_id:      int = Query(),
    key:            str = Query(),
    limit:          int = Query(),
    from_id:        int = Query(),
    group:          str = Query(),
    document_type:  str = Query(),
):
    """获取支付详情 → 解析 → 存储。"""

    if seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    shop = shops[seller_id]

    try:
        resp = await Billing(shop).Billing(key=key, group=group, document_type=document_type, limit=limit, from_id=from_id)
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"get mercado billing failed for shop {seller_id}",
            error = {
                "type":         type(e).__name__,        # 异常类型
                "message":      str(e),                  # 异常消息
                "traceback":    traceback.format_exc(),  # 完整堆栈
            },
        )

    return ApiResponse(
        success=True,
        message="successfully get mercado billing",
        data=resp,
    )

@router.get("/mercado/shops/Periods/billing/sync/", response_model=ApiResponse)
async def sync_billing(
    shops                = Depends(get_shops),
    seller_id:       int = Query(),
    key:             str = Query(),
):
    """获取支付详情 → 解析 → 存储。"""

    targets = [shops.get(seller_id)] if seller_id in shops else shops.values()

    for shop in targets:
        try:
            await Billing(shop).sync_billing(key = key)
        except Exception as e:
            return ApiResponse(
                success=False,
                message=f"sync mercado billing failed for shop {seller_id}",
                error = {
                    "type":         type(e).__name__,        # 异常类型
                    "message":      str(e),                  # 异常消息
                    "traceback":    traceback.format_exc(),  # 完整堆栈
                },
            )

    return ApiResponse(
        success=True,
        message="successfully sync mercado billing",
    )

@router.get("/mercado/shops/billing/Periods/sync/", response_model=ApiResponse)
async def sync_periods(
    shops          = Depends(get_shops),
    seller_id: int = Query(),
):
    """获取支付详情 → 解析 → 存储。"""

    targets = [shops.get(seller_id)] if seller_id in shops else shops.values()

    for shop in targets:
        try:
            await Billing(shop).sync_periods()
        except Exception as e:
            return ApiResponse(
                success=False,
                message=f"sync mercado billing periods failed for shop {seller_id}",
                error = {
                    "type":         type(e).__name__,        # 异常类型
                    "message":      str(e),                  # 异常消息
                    "traceback":    traceback.format_exc(),  # 完整堆栈
                },
            )

    return ApiResponse(
        success=True,
        message="successfully sync mercado billing periods",
    )
