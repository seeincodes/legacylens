"""Connection pool for PostgreSQL via psycopg2."""
import logging
import threading
from contextlib import contextmanager

import psycopg2.pool
from pgvector.psycopg2 import register_vector

from app.config import settings

logger = logging.getLogger("legacylens.db")

_pool: psycopg2.pool.ThreadedConnectionPool | None = None
_pool_lock = threading.Lock()


def _init_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:  # double-checked locking
                _pool = psycopg2.pool.ThreadedConnectionPool(
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
        _pool.putconn(conn, close=conn.closed)


@contextmanager
def get_connection():
    """Yield a connection from the pool; always returns it when done."""
    conn = get_conn()
    try:
        yield conn
    finally:
        put_conn(conn)


def _reset_pool():
    """Close and discard the pool. Used in tests and shutdown."""
    global _pool
    if _pool is not None:
        _pool.closeall()
    _pool = None
