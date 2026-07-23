"""FastAPI 统一请求/响应 Pydantic 模型"""

import time
import contextvars
from datetime import datetime, timezone, timedelta

from pydantic import BaseModel, Field, model_validator

# ── 请求耗时 ──────────────────────────────────────────
# contextvars：每个请求独立存储，协程安全
_request_start: contextvars.ContextVar[float] = contextvars.ContextVar("request_start")


def _compute_elapsed() -> float:
    """计算从中间件记录的开始时间到现在的耗时。"""
    start = _request_start.get(None)
    if start is None:
        return 0.0
    return round(time.time() - start, 4)


# ── 通用响应 ──────────────────────────────────────────


class ApiResponse(BaseModel):
    """标准 API 响应包装。"""

    code:       int = 0             # 0=成功, 1=业务失败, -1=服务器异常
    message:    str = ""
    data:       dict | list | None = None
    elapsed:    float = Field(default_factory=_compute_elapsed)  # 自动计算耗时
    timestamp:  str = Field(default_factory=lambda: datetime.now().isoformat())


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

    Limit:              int | None = 1000
    Offset:             int | None = 0
    SellerSku:          str | None = None
    FacilityId:         str | None = None
    SellerWarehouseId:  str | None = None

# ── Mercado ──────────────────────────────────────────
class MLOrderSearch(BaseModel):
    """订单搜索参数。"""

    datatype:  int | None = None
    at:   datetime | None = None
    to:   datetime | None = None
    sort:      str | None = None
    item:      str | None = None
    status:    str | None = None
    seller:    str | None = None
    limit:     int | None = None
    offset:    int | None = None
    tags:      str | None = None
    q:         str | None = None

    @model_validator(mode='after')
    def set_default_dates(self):
        if self.datatype is None:
            self.datatype = 0
        now = datetime.now(tz=timezone.utc)
        if self.at is None:
            self.at = now - timedelta(hours=1)
        if self.to is None:
            self.to = now
        return self

# ── Paris ──────────────────────────────────────────
class PROrderSync(BaseModel):
    """订单同步参数。"""
    limit:              int | None = 100
    offset:             int | None = 0
    datatype:           int | None = 0
    at:                 datetime | None = None
    to:                 datetime | None = None

    @model_validator(mode='after')
    def set_default_dates(self):
        now = datetime.now(tz=timezone.utc)
        if self.at is None:
            self.at = now - timedelta(days=1)
        if self.to is None:
            self.to = now
        return self

class PROrderSearch(BaseModel):
    """订单搜索参数。"""
    limit:                  int | None = 100
    offset:                 int | None = 0
    gteUpdatedAt:           str | None = None  # utc
    lteUpdatedAt:           str | None = None  # utc
    gteCreatedAt:           str | None = None  # utc
    lteCreatedAt:           str | None = None  # utc
    gteCreatedAtInOrigin:   str | None = None  # utc
    lteCreatedAtInOrigin:   str | None = None  # utc
    orderNumber:            str | None = None
    subOrderNumber:         str | None = None
    customerDocument:       str | None = None
    status:                 int | None = None
    itemStatus:             list[str] | None = None
    orderByDispatchDate:    str | None = None
    facilityConfigId:       int | None = None

# ── Ripley ──────────────────────────────────────────
class RPOrderSync(BaseModel):
    """订单tsbu参数。"""
    max:                           int | None = 100
    offset:                        int | None = 0
    datatype:                      int | None = 0
    at:                       datetime | None = None
    to:                       datetime | None = None

    @model_validator(mode='after')
    def set_default_dates(self):
        now = datetime.now(tz=timezone.utc)
        if self.at is None:
            self.at = now - timedelta(hours=1)
        if self.to is None:
            self.to = now
        return self

class RPOrderSearch(BaseModel):
    """订单搜索参数。"""
    max:                           int | None = 100
    offset:                        int | None = 0
    start_update_date:             str | None = None  # utc
    end_update_date:               str | None = None  # utc
    start_date:                    str | None = None  # utc
    end_date:                      str | None = None  # utc
    order_ids:                     str | None = None
    order_state_codes:             str | None = None
    channel_codes:                 str | None = None
    only_null_channel:            bool | None = None
    customer_debited:             bool | None = None
    payment_workflow:              str | None = None
    has_incident:                 bool | None = None
    fulfillment_center_code:       str | None = None
    order_tax_mode:                str | None = None
    order_references_for_customer: str | None = None
    order_references_for_seller:   str | None = None

# ── walmart ──────────────────────────────────────────
class WMOrderSync(BaseModel):
    """订单搜索参数。"""
    limit:              int | None = 200
    datatype:           int | None = 0
    at:            datetime | None = None
    to:            datetime | None = None

    @model_validator(mode='after')
    def set_default_dates(self):
        now = datetime.now(tz=timezone.utc)
        if self.at is None:
            self.at = now - timedelta(hours=1)
        if self.to is None:
            self.to = now
        return self

class WMOrderSearch(BaseModel):
    """订单搜索参数。"""
    limit:                  int | None = 200
    lastModifiedStartDate:  str | None = None
    lastModifiedEndDate:    str | None = None
    createdStartDate:       str | None = None
    createdEndDate:         str | None = None
    fromExpectedShipDate:   str | None = None
    toExpectedShipDate:     str | None = None
    sku:                    str | None = None
    customerOrderId:        str | None = None
    purchaseOrderId:        str | None = None
    status:                 str | None = None
    productInfo:           bool | None = None
    shipNodeType:           str | None = None
    shippingProgramType:    str | None = None
    replacementInfo:       bool | None = None
    orderType:              str | None = None
    incentiveInfo:         bool | None = None
