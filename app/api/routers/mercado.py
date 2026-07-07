"""
Mercado Libre 路由: 商品/变体/订单/货运/库存/评价/账单/用户 共 7 个资源。

路由结构:
  GET /{shop_id}/order/sync                                       — 全量同步订单

"""
from fastapi import APIRouter, HTTPException, Query

from app.api.schemas import ApiResponse, MLOrderSearch
from app.http.client import HttpClient
from app.platform.MercadoShop import MercadoShop as Shop

from app.resources.mercado.order import Order

router = APIRouter()


# ═════════════════════════════════════════════════════════

@router.get("/paris/shop/order/sync", response_model=ApiResponse)
async def product_sync(
    searchmodel: MLOrderSearch = Query({}, description="订单搜索参数"),
):
    """全量同步商品: 拉取全部 item_id → 并发查详情 → 解析存储。"""
    search = {k: v for k, v in searchmodel.model_dump().items() if v is not None}
    for shop in shop_dep.values():
        try:
            await Order(shop).sync(search)
        except Exception:
            raise HTTPException(
                status_code=500,
                detail=f"mercado sync_orders failed for shop {shop.seller_id}",
            )

    return ApiResponse(success=True, message="mercado sync_orders done")
