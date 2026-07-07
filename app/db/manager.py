from typing import Dict, List, Sequence

from app.core.logging import get_logger
from app.db.pool import pool

logger = get_logger(__name__)


def _escape_ident(name: str) -> str:
    """字段名 / 表名加反引号; 已含反引号或特例 (`condition` 是保留字) 不重复。"""
    name = name.strip()
    if name.startswith("`") and name.endswith("`"):
        return name
    return f"`{name}`"


class DBManager:
    @classmethod
    async def select(cls, sql: str, params: Sequence | None = None) -> list[dict]:
        """执行 SELECT, 返回字典列表。"""
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, params)
                return await cur.fetchall()

    @classmethod
    async def insert(cls, table: str, rows: Dict | List) -> int:
        """批量插入 (INSERT IGNORE), 返回影响行数。空列表返回 0。"""
        if not rows:
            return 0
        dicts = [_to_dict(r) for r in rows]
        cols = list(dicts[0].keys())
        cols_str = ", ".join(_escape_ident(c) for c in cols)
        placeholders = ", ".join(["%s"] * len(cols))
        sql = f"INSERT IGNORE INTO {_escape_ident(table)} ({cols_str}) VALUES ({placeholders})"
        values = [tuple(d.get(c) for c in cols) for d in dicts]
        async with pool.acquire() as conn:
            try:
                async with conn.cursor() as cur:
                    affected = await cur.executemany(sql, values)
                await conn.commit()
                return affected
            except Exception as e:
                await conn.rollback()
                raise e

    @classmethod
    async def upsert(
        cls, table: str, dicts: Dict | List, conflict_cols: Sequence[str]
    ) -> int:
        """批量插入或更新 (ON DUPLICATE KEY UPDATE)。

        conflict_cols: 唯一索引字段, 冲突时不更新; 其余字段更新为 VALUES(col)。
        """
        if not dicts:
            return 0

        if isinstance(dicts, dict):
            dicts = [dicts]

        all_cols = list(dicts[0].keys())
        conflict_set = set(conflict_cols)
        update_cols = [c for c in all_cols if c not in conflict_set]
        if not update_cols:
            return 0

        cols_str = ", ".join(_escape_ident(c) for c in all_cols)
        placeholders = ", ".join(["%s"] * len(all_cols))
        update_str = ", ".join(
            f"{_escape_ident(c)} = new.{_escape_ident(c)}" for c in update_cols
        )
        sql = (
            f"INSERT INTO {_escape_ident(table)} ({cols_str}) "
            f"VALUES ({placeholders}) AS new "
            f"ON DUPLICATE KEY UPDATE {update_str}"
        )
        values = [tuple(d.get(c) for c in all_cols) for d in dicts]
        async with pool.acquire() as conn:
            try:
                async with conn.cursor() as cur:
                    await cur.executemany(sql, values)
                    affected = cur.rowcount
                await conn.commit()
                return affected
            except Exception as e:
                await conn.rollback()
                raise e

    @classmethod
    async def execute(cls, sql: str, params: Sequence | None = None) -> int:
        """执行 SQL 语句, 返回影响行数。"""
        async with pool.acquire() as conn:
            try:
                async with conn.cursor() as cur:
                    await cur.execute(sql, params)
                    affected = cur.rowcount
                await conn.commit()
                return affected
            except Exception as e:
                await conn.rollback()
                raise e

    @classmethod
    async def callproc(cls, proc_name: str, args: Sequence = ()) -> list[dict]:
        """调用存储过程, 返回结果集 (字典列表)。"""
        async with pool.acquire() as conn:
            try:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.callproc(proc_name, args)
                    result = await cur.fetchall()
                await conn.commit()
                return result
            except Exception as e:
                await conn.rollback()
                raise e
