from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import SQLAlchemyError

SCHEMA_NOT_CURRENT_MESSAGE = (
    "The database schema is behind this release: migration 0004_sync_removed_at "
    "(sections.removed_at) has not been applied. The operator must apply it manually "
    "(see docs/runbooks/hosted-beta-operations.md) before this process can start."
)

_PROBE = text("SELECT removed_at FROM sections LIMIT 0")


class SchemaNotCurrentError(RuntimeError):
    """Raised when the connected database lacks a column the sync-era code requires."""


def require_sync_schema(bind: Engine | Connection) -> None:
    """Fail fast when migration 0004_sync_removed_at has not been applied.

    The message is fixed on purpose: it never includes the connection URL or the driver
    error text, so it is safe to log and to surface from a startup failure.
    """
    try:
        if isinstance(bind, Engine):
            with bind.connect() as connection:
                connection.execute(_PROBE)
        else:
            with bind.begin_nested():
                bind.execute(_PROBE)
    except SQLAlchemyError as exc:
        raise SchemaNotCurrentError(SCHEMA_NOT_CURRENT_MESSAGE) from exc
