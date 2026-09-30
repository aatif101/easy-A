"""Single-sweep mutual exclusion via a transaction-scoped PostgreSQL advisory lock.

Render runs the old and new worker side by side for 60-90 seconds on every deploy, so two
sweeps could otherwise overlap (PROJECT.md D-22(c)). The lock must be ``pg_try_advisory_xact_lock``:
Supabase's transaction pooler (port 6543) hands each transaction to any server connection, so a
session-level lock would be silently lost between transactions.

``try_sweep_lock`` must be the first locking statement of the sweep transaction. The lock is
released automatically when that transaction commits or rolls back. Session-level advisory locks
(``pg_advisory_lock`` and ``pg_try_advisory_lock``) are forbidden here.

This module must stay light: no pandas and nothing from ``easy_a.refresh``.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

SYNC_LOCK_KEY = 0x45415359_4E43
"""Stable positive bigint: the ASCII bytes of "EASYNC". Never change it while a worker runs."""


def try_sweep_lock(session: Session) -> bool:
    """Take the sweep lock for the current transaction; False means another sweep holds it.

    Returns True on non-PostgreSQL databases (SQLite tests), where there is no second writer.
    """
    if session.get_bind().dialect.name != "postgresql":
        return True
    acquired = session.scalar(
        text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": SYNC_LOCK_KEY}
    )
    return bool(acquired)
