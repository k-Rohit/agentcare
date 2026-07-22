from functools import lru_cache

from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

from config import get_settings


@lru_cache(maxsize=1)
def get_checkpointer() -> PostgresSaver:
    """Return the shared LangGraph Postgres checkpointer.

    Persists graph state per thread_id (= workflow_run_id) into the Supabase
    Postgres database, so an interrupted run (e.g. Appointment waiting for a
    slot choice) can be resumed later. Uses a direct Postgres connection
    (DATABASE_URL), not the REST API — a different connection path from the
    rest of the app.

    Call setup_checkpointer() once, before first use, to create the
    checkpoint tables.
    """
    settings = get_settings()
    pool = ConnectionPool(
        conninfo=settings.database_url,
        max_size=5,
        kwargs={"autocommit": True, "prepare_threshold": None},
    )
    return PostgresSaver(pool)


def setup_checkpointer() -> None:
    """Create the checkpointer's tables. Run once (idempotent)."""
    get_checkpointer().setup()
