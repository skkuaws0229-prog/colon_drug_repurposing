from __future__ import annotations

import os
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError


DEFAULT_POSTGRES = {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "Drug",
    "POSTGRES_USER": "Drug",
    "POSTGRES_PASSWORD": "1234",
}


def env(name: str) -> str:
    return os.getenv(name, DEFAULT_POSTGRES[name])


def postgres_url() -> str:
    user = env("POSTGRES_USER")
    password = quote_plus(env("POSTGRES_PASSWORD"))
    host = env("POSTGRES_HOST")
    port = env("POSTGRES_PORT")
    db = env("POSTGRES_DB")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(postgres_url(), future=True, pool_pre_ping=True)


@contextmanager
def get_conn() -> Iterator[Any]:
    conn = get_engine().connect()
    try:
        yield conn
    finally:
        conn.close()


def fetch_all(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(text(query), params or {}).mappings().all()
        return [dict(row) for row in rows]


def fetch_one(query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute(text(query), params or {}).mappings().first()
        return dict(row) if row else None


def ping() -> bool:
    with get_conn() as conn:
        value = conn.execute(text("SELECT 1 AS ok")).mappings().one()["ok"]
        return int(value) == 1


__all__ = [
    "SQLAlchemyError",
    "fetch_all",
    "fetch_one",
    "ping",
]
