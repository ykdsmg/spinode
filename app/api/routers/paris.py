"""Paris 路由: 订单/商品/变体/货运/库存/评价/账单/用户 共 8 个资源。

路由结构:
  # Order
  GET  /paris/shop/order/sync                   — 全量同步订单
  GET  /paris/shop/{seller_id}/order/search     — 搜索订单

"""
# package
# import json

# fastapi
from fastapi import APIRouter, HTTPException, Query, Path, Request, Depends

# basemodel
from app.api.schemas import ApiResponse, PROrderSearch

# 店铺
from app.platform.ParisShop import ParisShop

# 资源
from app.resources.paris.order import Order





router = APIRouter()

def get_shops(request: Request):
    return request.app.state.paris_shops


# ═════════════════════════════════════════════════════════
#  Order
# ═════════════════════════════════════════════════════════


@router.get("/paris/shop/orders/sync", response_model=ApiResponse)
async def order_sync(
    seller_id: str | None = Query(default=None),
    shops = Depends(get_shops),
    searchmodel: PROrderSearch = Depends(),
):
    """同步订单"""
    search = searchmodel.model_dump(exclude_none=True)

    if seller_id and seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    targets = [shops.get(seller_id)] if seller_id in shops else shops.values()

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



@router.get("/paris/shop/{seller_id}/order/search",response_model=ApiResponse)
async def order_search(
    seller_id: str = Path(description="SELLER ID 必填"),
    shops: dict[str, ParisShop] = Depends(get_shops),
    searchmodel: PROrderSearch = Depends(),
):
    """
    查询并保存指定店铺的订单数据
    """
    if seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    shop = shops[seller_id]
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
