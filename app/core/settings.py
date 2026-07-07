import json

def load_settings():
    """从 JSON 加载配置; 文件缺失时使用默认值。"""
    cfg_path = "config.json"

    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f) or {}


def get_settings():
    """获取全局单例配置 (供不方便传参的场景使用)。"""
    return load_settings()
