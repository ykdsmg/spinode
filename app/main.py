"""
FastAPI 应用主文件。
"""
from fastapi            import FastAPI
from contextlib         import asynccontextmanager
from app.config         import load_paris_shop, load_falabella_shop, load_mercado_shop
from app.core.logging   import get_logger,setup_logging
from app.db.pool        import pool

from app.api.routers.falabella  import router as fl_router
from app.api.routers.mercado    import router as ml_router
from app.api.routers.paris      import router as ps_router

logger = get_logger(__name__)




@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期: 启动加载→运行→关闭清理。"""

    # ── startup ───────────────────────
    setup_logging()
    logger.info("fmshop v2.0 (FastAPI) 启动中...")
    await pool.create()
    logger.info("数据库连接池已就绪")

    # load all shops
    app.state.paris_shops       = await load_paris_shop()
    app.state.falabella_shops   = await load_falabella_shop()
    app.state.mercado_shops     = await load_mercado_shop()


    # ── 服务运行中 ──────────────
    yield

    # ── shutdown ──────────────────────
    await pool.close()
    logger.info("fmshop 已关闭")


# ── FastAPI 实例 ────────────────────────────────────
app = FastAPI(
    title="fmshop API",
    description="多电商平台数据同步系统 — REST API",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── 注册路由 ─────────────────────────────────────────
# app.include_router(fl_router, tags=["Falabella"])
# app.include_router(ml_router, tags=["Mercado"])
app.include_router(ps_router, tags=["Paris"])
