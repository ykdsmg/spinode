"""
Falabella 路由: 订单/商品/库存 共 3 个资源。

路由结构:
  GET  /falabella/orders/sync              — 全量同步订单
  GET  /falabella/order/{order_id}         — 获取单个订单
  GET  /falabella/orders/search            — 搜索订单
  GET  /falabella/orderitem/{order_id}     — 获取订单商品(item)
  GET  /falabella/orderitems/{order_ids}   — 获取订单商品列表(items)
  GET  /falabella/products/search          — 搜索商品
  GET  /falabella/products/sync            — 全量同步商品
  GET  /falabella/stocks/search            — 搜索库存
  GET  /falabella/stocks/sync              — 全量同步库存
"""

# package
# import json

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

    targets = [shops.get(seller_id)] if seller_id in shops else shops.values()

    for shop in targets:
        try:
            await Order(shop).sync_order(search)
        except Exception as e:
            return ApiResponse(
                code=1,
                message=f"sync orders failed: {type(e).__name__}: {str(e)}",
            )

    return ApiResponse(
        code=0,
        message="sync orders success",
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
            code=1,
            message=f"get order failed: {type(e).__name__}: {str(e)}",
        )

    return ApiResponse(
        code=0,
        message="get order success",
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
            code=1,
            message=f"get orders failed: {type(e).__name__}: {str(e)}",
        )

    return ApiResponse(
        code=0,
        message="get orders success",
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
            code=1,
            message=f"get order items failed: {type(e).__name__}: {str(e)}",
        )

    return ApiResponse(
        code=0,
        message="get order items success",
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
            code=1,
            message=f"get order items failed: {type(e).__name__}: {str(e)}",
        )

    return ApiResponse(
        code=0,
        message="get order items success",
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
            code=1,
            message=f"get products failed: {type(e).__name__}: {str(e)}",
        )

    return ApiResponse(
        code=0,
        message="get products success",
        data=resp,
    )


@router.get("/falabella/products/sync", response_model=ApiResponse)
async def product_sync(
    searchmodel: FLProductSearch = Depends(),
    shops=Depends(get_shops),
    seller_id: str = Query(default=None),
):
    """获取单个订单详情。"""
    targets = [shops.get(seller_id)] if seller_id in shops else shops.values()

    search = searchmodel.model_dump(exclude_none=True)

    for shop in targets:
        try:
            await Product(shop).sync_products(search)
        except Exception as e:
            return ApiResponse(
                code=1,
                message=f"sync products failed: {type(e).__name__}: {str(e)}",
            )

    return ApiResponse(
        code=0,
        message="sync products success",
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
            code=1,
            message=f"get stocks failed: {type(e).__name__}: {str(e)}",
        )

    return ApiResponse(
        code=0,
        message="get stocks success",
        data=resp,
    )

@router.get("/falabella/stocks/sync", response_model=ApiResponse)
async def stocks_sync(
    searchmodel: FLStockSearch = Depends(),
    shops=Depends(get_shops),
    seller_id: str = Query(default=None),
):
    """获取单个订单详情。"""
    search = searchmodel.model_dump(exclude_none=True)

    if seller_id and seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    targets = [shops.get(seller_id)] if seller_id in shops else shops.values()

    for shop in targets:
        try:
            await Stock(shop).sync_stocks(search)
        except Exception as e:
            return ApiResponse(
                code=1,
                message=f"sync stocks failed: {type(e).__name__}: {str(e)}",
            )

    return ApiResponse(
        code=0,
        message="sync stocks success",
    )
