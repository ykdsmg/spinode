"""FastAPI 统一请求/响应 Pydantic 模型"""

from datetime import datetime, timezone, timedelta

from pydantic import BaseModel, Field

# ── 通用响应 ──────────────────────────────────────────


class ApiResponse(BaseModel):
    """标准 API 响应包装。"""

    success:        bool = True
    message:        str = ""
    data:           dict | list | None = None
    error:          dict | None = None
    timestamp:      str = Field(default_factory=lambda: datetime.now().isoformat())


# ── falabella ──────────────────────────────────────────
class FLOrderSearch(BaseModel):
    """订单搜索参数。"""

    datatype:           int | None = 0
    at:            datetime | None = None
    to:            datetime | None = None
    Limit:              int | None = 100
    Offset:             int | None = 0
    Status:             str | None = None
    SortBy:             str | None = None
    SortDirection:      str | None = "asc"
    ShippingType:       str | None = None


class FLProductSearch(BaseModel):
    """商品搜索参数。"""

    Limit:              int | None = 1000
    Offset:             int | None = 0
    Filter:             str | None = "all"
    Search:             str | None = None
    SkuSellerList:      list[str] | None = None
    CreatedAfter:       str | None = None
    CreatedBefore:      str | None = None
    UpdatedAfter:       str | None = None
    UpdatedBefore:      str | None = None
    GlobalIdentifier:   int | None = 0


class FLStockSearch(BaseModel):
    """stock"""

    Limit:              int | None = None
    Offset:             int | None = None
    SellerSku:          str | None = None
    FacilityId:         str | None = None
    SellerWarehouseId:  str | None = None

# ── Mercado ──────────────────────────────────────────
class MLOrderSearch(BaseModel):
    """订单搜索参数。"""

    datatype:  int | None = 0
    at:   datetime | None = Field(default_factory=lambda: datetime.now(tz=timezone.utc) - timedelta(minutes=30))
    to:   datetime | None = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    sort:      str | None = "date_asc"
    item:      str | None = None
    status:    str | None = None
    seller:    str | None = None
    limit:     int | None = None
    offset:    int | None = None
    tags:      str | None = None
    q:         str | None = None

# ── Paris ──────────────────────────────────────────
class PROrderSearch(BaseModel):
    """订单搜索参数。"""

    orderNumber:        str | None = None
    subOrderNumber:     str | None = None
    sellerId:           str | None = None
    datatype:           int | None = None
    at:                 datetime | None = None
    to:                 datetime | None = None
    customerDocument:   str | None = None
    status:             int | None = None
    itemStatus:         list[str] | None = None
    orderByDispatchDate:str | None = None
    facilityConfigId:   int | None = None
    limit:              int | None = None
    offset:             int | None = None
