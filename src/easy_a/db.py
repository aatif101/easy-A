from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from easy_a.config import get_settings, normalize_database_url

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


SUPABASE_POOLER_PORT = 6543


def is_transaction_pooler(url: str) -> bool:
    """True for Supabase/Supavisor transaction-pooler URLs (no prepared statements)."""
    parsed = make_url(url)
    host = parsed.host or ""
    return parsed.port == SUPABASE_POOLER_PORT or "pooler.supabase.com" in host


def get_engine(database_url: str | None = None) -> Engine:
    settings = get_settings()
    url = normalize_database_url(database_url) if database_url else settings.require_database_url()
    kwargs: dict[str, object] = {"echo": settings.echo_sql, "pool_pre_ping": True}
    if url.startswith("postgresql+psycopg") and is_transaction_pooler(url):
        # Transaction poolers cannot serve server-side prepared statements.
        kwargs["connect_args"] = {"prepare_threshold": None}
    return create_engine(url, **kwargs)


def get_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    return sessionmaker(bind=engine or get_engine(), expire_on_commit=False)


@contextmanager
def session_scope(session_factory: sessionmaker[Session] | None = None) -> Iterator[Session]:
    factory = session_factory or get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
