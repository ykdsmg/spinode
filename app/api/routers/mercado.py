"""
Mercado Libre 路由: 商品/变体/订单/货运/库存/评价/账单/广告 共 7 个资源。

路由结构:
  GET /{shop_id}/order/sync                                       — 全量同步订单

"""
# package
# import json

# fastapi
from fastapi import APIRouter, HTTPException, Query, Request, Depends

# basemodel
from app.api.schemas import ApiResponse


# 资源
from app.resources.mercado.advertise import Advertise

router = APIRouter()
def get_shops(request: Request):
    return request.app.state.mercado_shops


# ═════════════════════════════════════════════════════════
# Advertise
# ═════════════════════════════════════════════════════════

@router.get("/mercado/ads/advertisers/sync", response_model=ApiResponse)
async def advertise_sync(
    request: Request,
    shops=Depends(get_shops),
    seller_id: int = Query(None, description="同步指定店铺, 默认None同步所有店铺"),
    PRODUCT_ID: str = Query(),
):
    """全量同步商品: 拉取全部 item_id → 并发查详情 → 解析存储。"""
    session = request.app.state.http_session
    targets = [shops.get(seller_id)] if seller_id else shops.values()

    for shop in targets:
        try:
            await Advertise(shop).sync_advertisers(session, PRODUCT_ID)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"sync mercado shop's advertisers failed for shop {shop.seller_id}  error:{e}",
            )

    return ApiResponse(success=True, message="sync mercado shop's advertisers done")

@router.get("/mercado/ads/adgroups/sync", response_model=ApiResponse)
async def adgroups_sync(
    request: Request,
    shops=Depends(get_shops),
    seller_id: int = Query(None, description="同步指定店铺, 默认None同步所有店铺"),
):
    if seller_id is not None and seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    session = request.app.state.http_session
    targets = [shops.get(seller_id)] if seller_id else shops.values()

    for shop in targets:
        try:
            await Advertise(shop).sync_adgroups(session)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"sync Mercado adgroups failed for shop {shop.seller_id}: {e}",
            )

    return ApiResponse(
        success=True,
        message="successfully get Mercado adgroups",
    )

@router.get("/mercado/ads/adgroups/details/sync", response_model=ApiResponse)
async def adgroups_details_sync(
    request: Request,
    shops=Depends(get_shops),
    seller_id: int = Query(None, description="同步指定店铺, 默认None同步所有店铺"),
    data_at: str = Query(None, description="开始日期 YYYY-MM-DD"),
    data_to: str = Query(None, description="结束日期 YYYY-MM-DD"),
):
    if seller_id is not None and seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    session = request.app.state.http_session
    targets = [shops.get(seller_id)] if seller_id else shops.values()

    for shop in targets:
        try:
            await Advertise(shop).sync_adgroup_details(session, data_at, data_to)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"sync Mercado adgroups details failed for shop {shop.seller_id}: {e}",
            )

    return ApiResponse(
        success=True,
        message="successfully sync Mercado adgroups details",
    )


@router.get("/mercado/ads/advertisers/search", response_model=ApiResponse)
async def advertise_search(
    request: Request,
    shops=Depends(get_shops),
    seller_id: int = Query(),
    product_id: str = Query(),
):
    if seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    session = request.app.state.http_session
    shop = shops[seller_id]

    try:
        resp = await Advertise(shop).get_advertisers(session, product_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"search Mercado advertisers failed for shop {seller_id}: {e}",
        )

    return ApiResponse(
        success=True,
        message="successfully get Mercado advertisers",
        data=resp,
    )

@router.get("/mercado/ads/adgroups/search", response_model=ApiResponse)
async def adgroups_search(
    request: Request,
    shops=Depends(get_shops),
    seller_id: int = Query(),
    advertiser_site_id: str = Query(),
    advertiser_id: str = Query(),
    limit: int = Query(default=100),
    offset: int = Query(default=0),
    data_at: str = Query(),
    data_to: str = Query(),
):
    if seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    session = request.app.state.http_session
    shop = shops[seller_id]

    try:
        resp = await Advertise(shop).get_adgroups(session, advertiser_site_id, advertiser_id, limit, offset, data_at, data_to)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"search Mercado adgroups failed for shop {seller_id}: {e}",
        )

    return ApiResponse(
        success=True,
        message="successfully get Mercado adgroups",
        data=resp,
    )

@router.get("/mercado/ads/adgroup/details/search", response_model=ApiResponse)
async def adgroups_details_search(
    request: Request,
    shops=Depends(get_shops),
    seller_id: int = Query(),
    advertiser_site_id: str = Query(),
    ad_group_id: str = Query(),
    data_at: str = Query(),
    data_to: str = Query(),
):
    if seller_id not in shops:
        raise HTTPException(status_code=404, detail="shop not found")

    session = request.app.state.http_session
    shop = shops[seller_id]

    try:
        resp = await Advertise(shop).get_adgroup_details(session, advertiser_site_id, ad_group_id, data_at, data_to)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"search Mercado adgroup_details failed for shop {seller_id}: {e}",
        )

    return ApiResponse(
        success=True,
        message="successfully get Mercado adgroup_details",
        data=resp,
    )
