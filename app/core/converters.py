"""
通用安全转换方法 (全平台共享)
"""
import json

def _trim(s):
    """截断 ISO 时间字符串到 'YYYY-MM-DD HH:MM:SS' 或 'YYYY-MM-DDTHH:MM:SS'。"""
    return s[:19] if s else None

def _json(s):
    """将对象转换为 JSON 字符串。"""
    return json.dumps(s, ensure_ascii=False) if s else None

def _str(s):
    """将对象转换为字符串。"""
    return str(s) if s else None

def _lstr(s):
    """将List对象转换为字符串。"""
    return ','.join(str(item) for item in s) if s else None

def _sdec(s):
    """str decimal"""
    return str(s).replace(",", "") if s else "0.00"
