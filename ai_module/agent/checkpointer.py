"""LangGraph PostgreSQL Checkpointer for tutor session persistence."""

import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def get_db_connection_string() -> str:
    """Get PostgreSQL connection string for psycopg (not asyncpg)."""
    db_url = os.getenv("DATABASE_URL", "")
    # Remove asyncpg driver spec - use psycopg instead
    conn_string = db_url.replace("+asyncpg", "").replace("postgresql+asyncpg", "postgresql")
    if not conn_string.startswith("postgresql"):
        conn_string = "postgresql" + conn_string.split("postgresql", 1)[-1] if "postgresql" in conn_string else conn_string
    return conn_string


async def get_checkpointer():
    """Create and setup AsyncPostgresSaver checkpointer."""
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    
    conn_string = get_db_connection_string()
    checkpointer = AsyncPostgresSaver.from_conn_string(conn_string)
    await checkpointer.setup()  # Creates checkpoint tables if not exist
    return checkpointer
