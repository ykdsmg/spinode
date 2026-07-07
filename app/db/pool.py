"""
aiomysql 单例连接池

启动时调用 pool.create(settings), 退出时 await pool.close()
所有数据库操作通过 pool.acquire() 获取连接, 上下文管理自动归还
"""

import aiomysql
from app.core.settings import get_settings
from app.core.logging import get_logger


logger = get_logger(__name__)
settings = get_settings()



class DatabasePool:
    """aiomysql 连接池单例。"""

    def __init__(self):
        self._pool: aiomysql.Pool | None = None

    async def create(self):
        """根据配置创建连接池。重复调用会先关闭旧池。"""
        if self._pool is not None:
            return self._pool
        self._pool = await aiomysql.create_pool(
            host=settings.get("host"),
            port=settings.get("port"),
            user=settings.get("user"),
            password=settings.get("password"),
            db=settings.get("database"),
            charset=settings.get("charset"),
            autocommit=settings.get("autocommit"),
            maxsize=settings.get("pool_size") or 10,
            minsize=2,
            pool_recycle=3600,
        )

    async def close(self) -> None:
        if self._pool is not None:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None
            logger.info("数据库连接池已关闭")

    def acquire(self):
        """获取连接 (上下文管理)。每次操作用完自动归还。"""
        if self._pool is None:
            raise RuntimeError("数据库连接池未初始化, 请先调用 pool.create(settings)")
        return self._pool.acquire()

# 全局单例
pool = DatabasePool()
