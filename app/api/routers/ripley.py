"""Ripley 路由: 订单/商品/变体/货运/库存/评价/账单/用户 共 8 个资源。

路由结构:
  # Order
  GET  /ripley/shop/{shop_id}/orders/search     — 搜索订单

"""
# package
# import json

# fastapi
from fastapi import APIRouter, HTTPException, Query, Path, Request, Depends

# basemodel
from app.api.schemas import ApiResponse, RPOrderSearch

# 资源
from app.resources.ripley.order import Order




router = APIRouter()

def get_shops(request: Request):
    return request.app.state.ripley_shops


# ═════════════════════════════════════════════════════════
#  Order
# ═════════════════════════════════════════════════════════
@router.get("/ripley/shop/{shop_id}/orders/search", response_model=ApiResponse)
async def order_search(
    shop_id: str = Path(description="SHOP ID 必填"),
    shops:  dict = Depends(get_shops),
    searchmodel: RPOrderSearch = Depends(),
):
    """
    查询并保存指定店铺的订单数据
    """
    if shop_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    shop = shops[shop_id]
    search = searchmodel.model_dump(exclude_none=True)

    try:
        resp = await Order(shop).search(search)
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


@router.get("/ripley/orders/sync", response_model=ApiResponse)
async def order_sync(
    shops                 = Depends(get_shops),
    shop_id:        int = Query(None, description="同步指定店铺, 默认None同步所有店铺"),
    searchmodel: RPOrderSearch = Depends(),
):
    """全量同步订单: 按日期范围分页拉取 → 解析 → 存储订单/商品/支付 → 并发拉取货运详情。"""

    targets = [shops.get(shop_id)] if shop_id in shops else shops.values()

    search = searchmodel.model_dump(exclude_none=True)

    for shop in targets:
        try:
            await Order(shop).sync(search)
        except Exception as e:
            return ApiResponse(
                code=1,
                message=f"sync orders failed: {type(e).__name__}: {str(e)}",
            )

    return ApiResponse(
        code=0,
        message="sync orders success",
    )
