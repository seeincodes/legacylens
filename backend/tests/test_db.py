import sys, os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db import get_conn, put_conn, _reset_pool


def test_get_conn_returns_connection():
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_pool.getconn.return_value = mock_conn

    with patch("app.db._pool", mock_pool), \
         patch("app.db.register_vector"):
        conn = get_conn()

    assert conn is mock_conn
    mock_pool.getconn.assert_called_once()


def test_put_conn_returns_to_pool():
    mock_pool = MagicMock()
    mock_conn = MagicMock()

    with patch("app.db._pool", mock_pool):
        put_conn(mock_conn)

    mock_pool.putconn.assert_called_once_with(mock_conn)


def test_reset_pool_clears_pool():
    _reset_pool()
    # After reset, get_conn should create a new pool
    # (tested via integration, but _reset_pool should not raise)
