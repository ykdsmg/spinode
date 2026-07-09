"""
通用安全转换方法 (全平台共享)
"""
import json

def _trim(s):
    """截断 ISO 时间字符串到 'YYYY-MM-DD HH:MM:SS'。"""
    return s[:19] if s else None

def _json(s):
    return json.dumps(s, ensure_ascii=False) if s else None

def _str(s):
    return str(s) if s else None
