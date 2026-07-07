"""
通用安全转换方法 (全平台共享)
"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Sequence, TypeVar

T = TypeVar("T")

_NONE = object()  # 哨兵, 与合法 None 区分


def safe_get(data: Any, *keys: str, default: Any = None) -> Any:
    """安全多层取值: safe_get(d, 'a', 'b', 'c') 等价于 d?.a?.b?.c。任一层为 None/缺失返回 default。"""
    cur: Any = data
    for k in keys:
        if cur is None or not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur if cur is not None else default


def to_str(value: Any, default: str | None = None) -> str | None:
    """转字符串; None / 空串返回 default。"""
    if value is None:
        return default
    s = str(value).strip()
    return s if s else default


def to_int(value: Any, default: int = 0) -> int | None:
    """安全转 int; 失败或空返回 default。"""
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default


def to_decimal(value: Any, default: str = "0") -> Decimal:
    """安全转 Decimal, 自动去除千分位逗号与空白。

    替代解析代码中反复出现的:
        Decimal((x or '0.00').replace(',', '').strip())
    """
    if value is None or value == "":
        return Decimal(default)
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)


def parse_datetime(value: Any, fmt: str | None = None) -> str | None:
    """解析 ISO 时间字符串, 统一输出 'YYYY-MM-DD HH:MM:SS'; 失败返回 None。

    支持 '2021-08-04T10:00:00Z' / '2021-08-04T10:00:00-04:00' / 无时区形式。
    fmt 指定时按 fmt 解析。
    """
    if not value:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    s = str(value).strip()
    if not s:
        return None
    # 去掉 ISO 末尾的 Z (fromisoformat 在 3.11 前不支持)
    iso = s.replace("Z", "+00:00") if s.endswith("Z") else s
    try:
        if fmt:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d %H:%M:%S")
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return None


def as_list(value: Any) -> list:
    """把接口返回的单对象 / None 统一成 list。

    许多电商接口在仅一条记录时返回 dict 而非 list, 此处统一规整。
    """
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    return [value]


def join_csv(value: Any, sep: str = ",") -> str | None:
    """把 list/可迭代对象用 sep 连接为字符串; 空则 None。元素转 str。"""
    if value is None:
        return None
    if isinstance(value, str):
        return value if value else None
    if isinstance(value, (list, tuple, set)):
        parts = [str(v) for v in value if v is not None]
        return sep.join(parts) if parts else None
    return str(value)


def to_json_str(value: Any) -> str | None:
    """序列化为 JSON 字符串; None 输入返回 None。"""
    if value is None:
        return None
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return None


def from_json(value: Any, default: Any = None) -> Any:
    """安全 JSON 解析; 失败返回 default。"""
    if not value:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


def first(seq: Sequence[T], default: Any = None) -> T | Any:
    """取序列第一个元素; 空则 default。"""
    return seq[0] if seq else default
