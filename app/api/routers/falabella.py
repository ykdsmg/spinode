"""
Falabella 路由:

路由结构:
  GET  /falabella/order/{order_id}           — 获取单个订单
"""

# package
# import json

# fastapi
from fastapi import APIRouter, HTTPException, Query, Request, Depends

# basemodel
from app.api.schemas import ApiResponse, FLOrderSearch


# 资源
from app.resources.falabella.order import Order


router = APIRouter()
def get_shops(request: Request):
    return request.app.state.falabella_shops


# ═════════════════════════════════════════════════════════
#  Order
# ═════════════════════════════════════════════════════════
@router.get("/falabella/order/sync", response_model=ApiResponse)
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
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"sync falabella order failed for shop {shop.seller_id}: {e}",
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"get falabella order failed for shop {seller_id}: {e}",
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"get falabella order failed for shop {seller_id}: {e}",
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"get falabella order - item failed for shop {seller_id}: {e}",
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"get falabella order - items failed for shop {seller_id}: {e}",
        )

    return ApiResponse(
        success=True,
        message="successfully get falabella order - items",
        data=resp,
    )
