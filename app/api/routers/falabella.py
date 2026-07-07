"""
Falabella 路由:

路由结构:
  GET  /falabella/shop/product/sync           — 同步产品
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Path

from app.api.schemas import ApiResponse, FLProductSearch
from app.http.client import HttpClient
from app.platform.FalabellaShop import FalabellaShop as Shop
from app.resources.falabella.product import Product

router = APIRouter()


# ═════════════════════════════════════════════════════════
#  Product
# ═════════════════════════════════════════════════════════
@router.get("/falabella/shop/product/sync", response_model=ApiResponse)
async def product_sync(search: FLProductSearch = Query({}, description="商品搜索参数")):

    client = HttpClient()
    for shop in shop_dep.values():
        try:
            await Product(shop, client).sync_products(search)
        except Exception:
            raise HTTPException(
                status_code=500,
                detail=f"sync_products failed for shop {shop.seller_id}",
            )

    return ApiResponse(success=True, message="sync_products done")


@router.get("/falabella/{shop_id}/product/sync", response_model=ApiResponse)
async def product_sync_by_shop_id(
    shop_id: Optional[str] = Path(description="Shop ID 为空则同步全部店铺"),
    search: FLProductSearch = Query({}, description="商品搜索参数"),
):

    if shop_id and shop_id not in shop_dep:
        raise HTTPException(status_code=404, detail="shop_id not found")
    client = HttpClient()
    try:
        await Product(shop_dep.get(shop_id), client).sync_products(search)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail=f"sync_products failed for shop {shop_id}",
        )

    return ApiResponse(success=True, message="sync_products done")


# ═════════════════════════════════════════════════════════
#  Order
# ═════════════════════════════════════════════════════════
