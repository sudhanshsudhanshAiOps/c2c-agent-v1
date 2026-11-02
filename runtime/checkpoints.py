# Schema-scoped LangGraph checkpoints using checked PostgreSQL connections.
"""Schema-scoped LangGraph checkpoints using checked PostgreSQL connections."""
from contextlib import asynccontextmanager
import logging
import os
import re

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import sql
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)


# Validate the configured PostgreSQL schema name before using it for checkpoints.
def checkpoint_schema():
    schema = os.getenv("SUPABASE_SCHEMA", "public")
    if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", schema):
        raise ValueError("SUPABASE_SCHEMA must be a lowercase PostgreSQL identifier")
    return schema


# Open the checked PostgreSQL connection pool and initialize the LangGraph checkpoint saver.
@asynccontextmanager
async def checkpoint_saver():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required for incident checkpoints")
    schema = checkpoint_schema()
    os.environ.setdefault("LANGGRAPH_STRICT_MSGPACK", "true")

    # Set the checkpoint connection search path to the validated application schema.
    async def configure(connection):
        await connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))

    async with AsyncConnectionPool(
        conninfo=database_url, min_size=1, max_size=3,
        kwargs={"autocommit": True, "prepare_threshold": 0, "connect_timeout": 5},
        configure=configure, check=AsyncConnectionPool.check_connection, open=False,
    ) as pool:
        await pool.wait(timeout=15)
        async with pool.connection() as connection:
            cursor = await connection.execute("SELECT current_schema()")
            if (await cursor.fetchone())[0] != schema:
                raise RuntimeError("Configured checkpoint schema is missing or inaccessible")
        saver = AsyncPostgresSaver(pool)
        await saver.setup()
        logger.info("Checkpoint pool ready: schema=%s", schema)
        yield saver
