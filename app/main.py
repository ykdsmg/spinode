"""
FastAPI 应用主文件。
"""

import time

from fastapi            import FastAPI
from contextlib         import asynccontextmanager
from app.config         import load_paris_shop, load_falabella_shop, load_mercado_shop
from app.core.logging   import get_logger,setup_logging
from app.db.pool        import pool
from curl_cffi.requests import AsyncSession, RetryStrategy

from starlette.requests import Request

from app.api.schemas           import _request_start
from app.api.routers.falabella import router as fl_router
from app.api.routers.mercado   import router as ml_router
from app.api.routers.paris     import router as ps_router

import requests
logger = get_logger(__name__)

# 全局 session 配置
_HTTP_MAX_CLIENTS   = 200            # 最大并发连接数
_HTTP_TIMEOUT       = 60             # 默认超时（秒）
_RETRY_COUNT        = 5              # 失败重试次数
_RETRY_DELAY        = 1.0            # 重试初始延迟（秒）
_RETRY_BACKOFF      = 'exponential'  # 重试退避策略


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期: 启动加载→运行→关闭清理。"""

    # ── startup ───────────────────────
    setup_logging()
    logger.info("spinode v2.0 (FastAPI) 启动中...")
    await pool.create()
    logger.info("数据库连接池已就绪")

    # 全局异步 HTTP Session（curl_cffi）
    async_session = AsyncSession(
        max_clients = _HTTP_MAX_CLIENTS,
        timeout     = _HTTP_TIMEOUT,
        retry       = RetryStrategy(
            count   = _RETRY_COUNT,
            delay   = _RETRY_DELAY,
            jitter  = 0.5,
            backoff = _RETRY_BACKOFF,
        ),
    )
    logger.info("异步 HTTP Session 已就绪 (max_clients=%s, retry=%s, timeout=%s)", _HTTP_MAX_CLIENTS, _RETRY_COUNT, _HTTP_TIMEOUT)

    # 全局同步 HTTP Session（curl_cffi）
    sync_session = requests.Session()
    logger.info("同步 HTTP Session 已就绪 (timeout=%s)", _HTTP_TIMEOUT)

    # 注入 app.state
    app.state.async_session = async_session
    app.state.sync_session = sync_session

    # load all shops
    app.state.paris_shops       = await load_paris_shop(async_session)
    app.state.falabella_shops   = await load_falabella_shop(sync_session)
    app.state.mercado_shops     = await load_mercado_shop(async_session)


    # ── 服务运行中 ──────────────
    yield

    # ── shutdown ──────────────────────
    await async_session.close()
    logger.info("异步 HTTP Session 已关闭")
    sync_session.close()
    logger.info("同步 HTTP Session 已关闭")
    await pool.close()
    logger.info("spinode 已关闭")


# ── FastAPI 实例 ────────────────────────────────────
app = FastAPI(
    title="spinode API",
    description="多电商平台数据同步系统 — REST API",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── 接口耗时中间件 ──────────────────────────────────
@app.middleware("http")
async def timing(request: Request, call_next):
    """记录每个请求的开始时间，elapsed 由 ApiResponse 自动计算。"""
    _request_start.set(time.time())
    return await call_next(request)


# ── 注册路由 ─────────────────────────────────────────
app.include_router(fl_router, tags=["Falabella"])
app.include_router(ml_router, tags=["Mercado"])
app.include_router(ps_router, tags=["Paris"])
