"""
通用安全转换方法 (全平台共享)
"""

def _trim(s):
    """截断 ISO 时间字符串到 'YYYY-MM-DD HH:MM:SS'。"""
    return s[:19] if s else None
