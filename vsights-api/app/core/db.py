"""Kết nối CSDL. Repository nhận Connection; Service quyết định giao dịch (with conn.begin())."""
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Connection, Engine, create_engine

from app.core.config import cai_dat


@lru_cache
def engine() -> Engine:
    return create_engine(cai_dat().database_url, pool_size=10, max_overflow=5, pool_pre_ping=True)


def lay_ket_noi() -> Iterator[Connection]:
    with engine().connect() as conn:
        yield conn
