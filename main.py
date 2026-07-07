"""Spinode v2.0 入口 —— FastAPI REST API 服务器。

启动:
    python main.py                  # 默认 host=0.0.0.0:8000
    python main.py --port 9000      # 自定义端口
    python main.py --reload         # 开发模式 (代码热重载)

也支持直接通过 uvicorn 启动:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""

import argparse
import uvicorn


def parse_args():
    p = argparse.ArgumentParser(description="fmshop API Server")
    p.add_argument("--host", default="0.0.0.0", help="监听地址 (默认 0.0.0.0)")
    p.add_argument("--port", type=int, default=8000, help="监听端口 (默认 8000)")
    p.add_argument("--reload", action="store_true", help="开发模式 (代码变动自动重启)")
    p.add_argument("--log-level", default="info", help="uvicorn 日志级别 (默认 info)")
    return p.parse_args()


def main():
    args = parse_args()
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
