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
from app.api.schemas import ApiResponse


# 资源
from app.resources.falabella.order import Order


router = APIRouter()
def get_shops(request: Request):
    return request.app.state.falabella_shops


# ═════════════════════════════════════════════════════════
#  Order
# ═════════════════════════════════════════════════════════
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
            detail=f"get mercado order failed for shop {seller_id}: {e}",
        )

    return ApiResponse(
        success=True,
        message="successfully get mercado order",
        data=resp,
    )
