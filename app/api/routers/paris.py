"""Paris 路由: 商品/变体/订单/货运/库存/评价/账单/用户 共 7 个资源。

路由结构:

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


@router.get("/paris/shop/order/sync", response_model=ApiResponse)
async def order_sync(
    shops=Depends(get_shops),
    searchmodel: PROrderSearch = Query({}, description="商品搜索参数"),
):
    """同步订单"""
    search = searchmodel.model_dump(exclude_none=True)

    for shop in shops.values():
            try:
                await Order(shop).sync(search)
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"sync paris orders failed for shop {shop.seller_id}: {e}",
                )

    return ApiResponse(success=True, message="sync paris orders done")



@router.get("/paris/shop/{seller_id}/order/search",response_model=ApiResponse)
async def order_search(
    seller_id: str = Path(description="SELLER ID 必填"),
    shops: dict[str, ParisShop] = Depends(get_shops),
    searchmodel: PROrderSearch = Query({}, description="订单搜索参数"),
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"search orders failed for shop {seller_id}: {e}",
        )

    return ApiResponse(
        success=True,
        message="search and save orders done",
        data=resp,
    )
