"""
Falabella 路由:

路由结构:
  GET  /falabella/shop/product/sync           — 同步产品
"""

# package
# import json

# fastapi
from fastapi import APIRouter, HTTPException, Query, Request, Depends

# basemodel
from app.api.schemas import ApiResponse


# 资源


router = APIRouter()
def get_shops(request: Request):
    return request.app.state.mercado_shops


# ═════════════════════════════════════════════════════════
#  Product
# ═════════════════════════════════════════════════════════
