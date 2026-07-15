"""
Falabella 路由:

路由结构:
  GET  /falabella/order/{order_id}           — 获取单个订单
"""

# package
# import json
import traceback

# fastapi
from fastapi import APIRouter, HTTPException, Query, Request, Depends

# basemodel
from app.api.schemas import ApiResponse, FLOrderSearch,FLProductSearch, FLStockSearch


# 资源
from app.resources.falabella.order import Order
from app.resources.falabella.product import Product
from app.resources.falabella.stock import Stock


router = APIRouter()
def get_shops(request: Request):
    return request.app.state.falabella_shops


# ═════════════════════════════════════════════════════════
#  Order
# ═════════════════════════════════════════════════════════
@router.get("/falabella/orders/sync", response_model=ApiResponse)
async def order_sync(
    shops = Depends(get_shops),
    searchmodel: FLOrderSearch = Depends(),
    seller_id: str = Query(None, description="同步指定店铺, 默认None同步所有店铺"),
):
    """获取单个订单详情。"""
    search = searchmodel.model_dump(exclude_none=True)
    if seller_id and seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    targets = [shops.get(seller_id)] if seller_id else shops.values()

    for shop in targets:
        try:
            await Order(shop).sync_order(search)
        except Exception as e:
            return ApiResponse(
                success=False,
                message=f"sync falabella order failed for shop {shop.seller_id}",
                error = {
                    "type":         type(e).__name__,        # 异常类型
                    "message":      str(e),                  # 异常消息
                    "traceback":    traceback.format_exc(),  # 完整堆栈
                },
            )

    return ApiResponse(
        success=True,
        message="successfully sync falabella order done",
    )

@router.get("/falabella/order/{order_id}", response_model=ApiResponse)
async def order_get(
    order_id: str,
    shops=Depends(get_shops),
    seller_id: str = Query(),
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
            message=f"get falabella order failed for shop {seller_id}",
            error = {
                "type":         type(e).__name__,        # 异常类型
                "message":      str(e),                  # 异常消息
                "traceback":    traceback.format_exc(),  # 完整堆栈
            },
        )

    return ApiResponse(
        success=True,
        message="successfully get falabella order",
        data=resp,
    )

@router.get("/falabella/orders/search", response_model=ApiResponse)
async def orders_search(
    searchmodel: FLOrderSearch = Query({}, description="商品搜索参数"),
    shops=Depends(get_shops),
    seller_id: str = Query(),
):
    """获取单个订单详情。"""
    search = searchmodel.model_dump(exclude_none=True)
    if seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    shop = shops[seller_id]

    try:
        resp = await Order(shop).get_orders(search)
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"get falabella order failed for shop {seller_id}",
            error = {
                "type":         type(e).__name__,        # 异常类型
                "message":      str(e),                  # 异常消息
                "traceback":    traceback.format_exc(),  # 完整堆栈
            },
        )

    return ApiResponse(
        success=True,
        message="successfully get falabella order",
        data=resp,
    )

@router.get("/falabella/orderitem/{order_id}", response_model=ApiResponse)
async def orderitem_get(
    order_id: str,
    shops=Depends(get_shops),
    seller_id: str = Query(),
):
    """获取单个订单详情。"""

    if seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    shop = shops[seller_id]

    try:
        resp = await Order(shop).get_item(order_id)
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"get falabella order - item failed for shop {seller_id}",
            error = {
                "type":         type(e).__name__,        # 异常类型
                "message":      str(e),                  # 异常消息
                "traceback":    traceback.format_exc(),  # 完整堆栈
            },
        )

    return ApiResponse(
        success=True,
        message="successfully get falabella order - item",
        data=resp,
    )

@router.get("/falabella/orderitems/{order_ids}", response_model=ApiResponse)
async def orderitems_search(
    order_ids: str,
    shops=Depends(get_shops),
    seller_id: str = Query(),
):
    """获取单个订单详情。"""
    if seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    shop = shops[seller_id]

    try:
        resp = await Order(shop).get_items(order_ids)
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"get falabella order - items failed for shop {seller_id}",
            error = {
                "type":         type(e).__name__,        # 异常类型
                "message":      str(e),                  # 异常消息
                "traceback":    traceback.format_exc(),  # 完整堆栈
            },
        )

    return ApiResponse(
        success=True,
        message="successfully get falabella order - items",
        data=resp,
    )

# ═════════════════════════════════════════════════════════
#  Product
# ═════════════════════════════════════════════════════════
@router.get("/falabella/products/search", response_model=ApiResponse)
async def product_search(
    searchmodel: FLProductSearch = Depends(),
    shops=Depends(get_shops),
    seller_id: str = Query(),
):
    """获取单个订单详情。"""
    search = searchmodel.model_dump(exclude_none=True)
    if seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    shop = shops[seller_id]

    try:
        resp = await Product(shop).get_products(search)
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"get falabella product failed for shop {seller_id}",
            error = {
                "type":         type(e).__name__,        # 异常类型
                "message":      str(e),                  # 异常消息
                "traceback":    traceback.format_exc(),  # 完整堆栈
            },
        )

    return ApiResponse(
        success=True,
        message="successfully get falabella product",
        data=resp,
    )


@router.get("/falabella/products/sync", response_model=ApiResponse)
async def product_sync(
    searchmodel: FLProductSearch = Depends(),
    shops=Depends(get_shops),
    seller_id: str = Query(),
):
    """获取单个订单详情。"""
    search = searchmodel.model_dump(exclude_none=True)
    if seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    shop = shops[seller_id]

    try:
        resp = await Product(shop).sync_products(search)
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"sync falabella products failed for shop {seller_id}",
            error = {
                "type":         type(e).__name__,        # 异常类型
                "message":      str(e),                  # 异常消息
                "traceback":    traceback.format_exc(),  # 完整堆栈
            },
        )

    return ApiResponse(
        success=True,
        message="successfully sync falabella products",
        data=resp,
    )


# ═════════════════════════════════════════════════════════
#  Stock
# ═════════════════════════════════════════════════════════
@router.get("/falabella/stocks/search", response_model=ApiResponse)
async def stocks_search(
    searchmodel: FLStockSearch = Depends(),
    shops=Depends(get_shops),
    seller_id: str = Query(),
):
    """获取单个订单详情。"""
    search = searchmodel.model_dump(exclude_none=True)
    if seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    shop = shops[seller_id]

    try:
        resp = await Stock(shop).get_stocks(search)
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"get falabella product stock failed for shop {seller_id}",
            error = {
                "type":         type(e).__name__,        # 异常类型
                "message":      str(e),                  # 异常消息
                "traceback":    traceback.format_exc(),  # 完整堆栈
            },
        )

    return ApiResponse(
        success=True,
        message="successfully get falabella product stock",
        data=resp,
    )

@router.get("/falabella/stocks/sync", response_model=ApiResponse)
async def stocks_sync(
    searchmodel: FLStockSearch = Depends(),
    shops=Depends(get_shops),
    seller_id: str = Query(),
):
    """获取单个订单详情。"""
    search = searchmodel.model_dump(exclude_none=True)
    if seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    shop = shops[seller_id]

    try:
        resp = await Stock(shop).sync_stocks(search)
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"sync falabella product stock failed for shop {seller_id}",
            error = {
                "type":         type(e).__name__,        # 异常类型
                "message":      str(e),                  # 异常消息
                "traceback":    traceback.format_exc(),  # 完整堆栈
            },
        )

    return ApiResponse(
        success=True,
        message="successfully sync falabella product stock",
        data=resp,
    )
