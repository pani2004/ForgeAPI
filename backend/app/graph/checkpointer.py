from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.config import DATABASE_URL

_pool: AsyncConnectionPool | None = None
_checkpointer: AsyncPostgresSaver | None = None


async def init_checkpointer() -> AsyncPostgresSaver:
    global _pool, _checkpointer

    if _checkpointer is not None:
        return _checkpointer

    _pool = AsyncConnectionPool(
        conninfo=DATABASE_URL,
        max_size=10,
        kwargs={
            "autocommit": True,
            "row_factory": dict_row,
        },
        open=False,
    )
    await _pool.open()

    _checkpointer = AsyncPostgresSaver(_pool)
    await _checkpointer.setup()
    return _checkpointer


def get_checkpointer() -> AsyncPostgresSaver:
    if _checkpointer is None:
        raise RuntimeError(
            "Checkpointer not initialized. Call init_checkpointer() first."
        )
    return _checkpointer


async def close_checkpointer() -> None:
    global _pool, _checkpointer

    if _pool is not None:
        await _pool.close()

    _pool = None
    _checkpointer = None
