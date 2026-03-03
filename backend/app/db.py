"""Connection pool for PostgreSQL via psycopg2."""
import logging

import psycopg2.pool
from pgvector.psycopg2 import register_vector

from app.config import settings

logger = logging.getLogger("legacylens.db")

_pool: psycopg2.pool.SimpleConnectionPool | None = None


def _init_pool() -> psycopg2.pool.SimpleConnectionPool:
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.SimpleConnectionPool(
            1, 10, settings.database_url,
        )
        logger.info("connection pool created (min=1, max=10)")
    return _pool


def get_conn():
    """Get a connection from the pool. Caller MUST call put_conn() when done."""
    pool = _init_pool()
    conn = pool.getconn()
    register_vector(conn)
    return conn


def put_conn(conn):
    """Return a connection to the pool."""
    if _pool is not None:
        _pool.putconn(conn)


def _reset_pool():
    """Close and discard the pool. Used in tests and shutdown."""
    global _pool
    if _pool is not None:
        _pool.closeall()
    _pool = None
