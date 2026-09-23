from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from easy_a.common.terms import TermParseError, normalize_banner_term_code
from easy_a.db import get_engine, get_session_factory


@lru_cache
def get_api_session_factory() -> sessionmaker[Session]:
    """One engine (and connection pool) per API process instead of one per request."""
    return get_session_factory(get_engine())


def get_db_session() -> Generator[Session, None, None]:
    session = get_api_session_factory()()
    try:
        yield session
    except SQLAlchemyError:
        session.rollback()
        raise
    finally:
        session.close()


def get_banner_term(
    term: Annotated[str, Query(description="Six-digit Banner term code, e.g. 202701.")],
) -> str:
    try:
        return normalize_banner_term_code(term)
    except TermParseError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


DbSession = Annotated[Session, Depends(get_db_session)]
BannerTerm = Annotated[str, Depends(get_banner_term)]
