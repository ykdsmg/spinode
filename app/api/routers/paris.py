"""Paris 路由: 商品/变体/订单/货运/库存/评价/账单/用户 共 7 个资源。

路由结构:

"""
import json

from fastapi import APIRouter, HTTPException, Query, Path

from app.api.config import load_paris_shop
from app.api.schemas import ApiResponse, PROrderSearch
from app.resources.paris.order import Order

router = APIRouter()

shop_dep = load_paris_shop()

# ═════════════════════════════════════════════════════════
#  Product
# ═════════════════════════════════════════════════════════


@router.get("/paris/shop/order/sync", response_model=ApiResponse)
async def order_sync(
    searchmodel: PROrderSearch = Query({}, description="商品搜索参数"),
):
    """全量同步商品: 拉取全部 item_id → 并发查详情 → 解析存储。"""
    search = {k: v for k, v in searchmodel.model_dump().items() if v is not None}
    for shop in shop_dep.values():
        try:
            await Order(shop).sync(search)
        except Exception:
            raise HTTPException(
                status_code=500,
                detail=f"sync_products failed for shop {shop.seller_id}",
            )

    return ApiResponse(success=True, message="sync_products done")

@router.get("/paris/shop/{SELLER_ID}/order/search", response_model=ApiResponse)
async def order_search(
    SELLER_ID: str = Path(description="SELLER ID 必填"),
    searchmodel: PROrderSearch = Query({}, description="商品搜索参数"),
):
    """全量同步商品: 拉取全部 item_id → 并发查详情 → 解析存储。"""
    search = {k: v for k, v in searchmodel.model_dump().items() if v is not None}
    shop = shop_dep.get(SELLER_ID)
    try:
        if not shop:
            raise HTTPException(status_code=404, detail="shop not found")
        resp = await Order(shop).searchorder(search)
        with open(f"data/{SELLER_ID}_order.json", "w", encoding="utf-8") as f:
            json.dump(resp, f, ensure_ascii=False, indent=4)
        return ApiResponse(success=True, message="search and save orders done", data=resp)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"search and save orders failed for shop {SELLER_ID}, error: {str(e)}",
        )
