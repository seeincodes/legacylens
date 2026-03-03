import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch, MagicMock
from app.services.understanding import (
    build_dependency_graph,
    lookup_routine,
    explain_routine,
    explain_routine_eli5,
    find_entry_points,
    find_data_usage,
    find_io_operations,
    find_error_patterns,
)


# --- lookup_routine tests ---

@patch("app.services.understanding._get_conn")
def test_lookup_routine_found(mock_conn):
    cur = MagicMock()
    cur.fetchone.return_value = (
        1, "SRC/dgesv.f", 1, 100, "DGESV", "driver",
        "SUBROUTINE DGESV...",
        {"calls": ["DGETRF", "DGETRS"]},
        [0.1] * 1536,
    )
    mock_conn.return_value.cursor.return_value = cur

    result = lookup_routine("DGESV")
    assert result is not None
    assert result["subroutine_name"] == "DGESV"
    assert result["calls"] == ["DGETRF", "DGETRS"]
    assert result["routine_type"] == "driver"


@patch("app.services.understanding._get_conn")
def test_lookup_routine_not_found(mock_conn):
    cur = MagicMock()
    cur.fetchone.return_value = None
    mock_conn.return_value.cursor.return_value = cur

    result = lookup_routine("NONEXISTENT")
    assert result is None


# --- build_dependency_graph tests ---

@patch("app.services.understanding._get_conn")
@patch("app.services.understanding.lookup_routine")
def test_dependency_graph_bfs(mock_lookup, mock_conn):
    mock_lookup.return_value = {
        "id": 1, "subroutine_name": "DGESV", "routine_type": "driver",
        "file_path": "SRC/dgesv.f", "calls": ["DGETRF", "DGETRS"],
        "content": "...", "metadata": {}, "embedding": [0.1] * 1536,
    }

    cur = MagicMock()
    # First call: DGETRF found
    # Second call: DGETRS found
    cur.fetchone.side_effect = [
        ("DGETRF", "computational", "SRC/dgetrf.f", {"calls": ["DLASWP"]}),
        ("DGETRS", "computational", "SRC/dgetrs.f", {"calls": []}),
    ]
    mock_conn.return_value.cursor.return_value = cur

    result = build_dependency_graph("DGESV", max_depth=1)
    assert result is not None
    assert result["root"] == "DGESV"
    assert len(result["nodes"]) == 3  # DGESV + DGETRF + DGETRS
    names = [n["name"] for n in result["nodes"]]
    assert "DGESV" in names
    assert "DGETRF" in names
    assert "DGETRS" in names


@patch("app.services.understanding._get_conn")
@patch("app.services.understanding.lookup_routine")
def test_dependency_graph_respects_max_depth(mock_lookup, mock_conn):
    mock_lookup.return_value = {
        "id": 1, "subroutine_name": "DGESV", "routine_type": "driver",
        "file_path": "SRC/dgesv.f", "calls": ["DGETRF"],
        "content": "...", "metadata": {}, "embedding": [0.1] * 1536,
    }

    cur = MagicMock()
    # DGETRF found at depth 1 — but has calls to DLASWP
    cur.fetchone.side_effect = [
        ("DGETRF", "computational", "SRC/dgetrf.f", {"calls": ["DLASWP"]}),
    ]
    mock_conn.return_value.cursor.return_value = cur

    # max_depth=1: should NOT traverse DLASWP (that would be depth 2)
    result = build_dependency_graph("DGESV", max_depth=1)
    names = [n["name"] for n in result["nodes"]]
    assert "DGESV" in names
    assert "DGETRF" in names
    assert "DLASWP" not in names


@patch("app.services.understanding.lookup_routine")
def test_dependency_graph_not_found(mock_lookup):
    mock_lookup.return_value = None
    result = build_dependency_graph("NONEXISTENT")
    assert result is None


# --- explain_routine tests ---

@patch("app.services.understanding.anthropic")
@patch("app.services.understanding.lookup_routine")
def test_explain_routine_calls_claude(mock_lookup, mock_anthropic):
    mock_lookup.return_value = {
        "id": 1, "subroutine_name": "DGESV", "routine_type": "driver",
        "file_path": "SRC/dgesv.f", "line_start": 1, "line_end": 100,
        "content": "SUBROUTINE DGESV...", "metadata": {},
        "calls": ["DGETRF", "DGETRS"], "embedding": [0.1] * 1536,
    }

    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.return_value.content = [
        MagicMock(text="DGESV solves a system of linear equations.")
    ]

    result = explain_routine("DGESV")
    assert result is not None
    assert result["subroutine_name"] == "DGESV"
    assert "DGESV solves" in result["explanation"]
    mock_client.messages.create.assert_called_once()


@patch("app.services.understanding.lookup_routine")
def test_explain_routine_not_found(mock_lookup):
    mock_lookup.return_value = None
    result = explain_routine("NONEXISTENT")
    assert result is None


@patch("app.services.understanding.anthropic")
@patch("app.services.understanding.lookup_routine")
def test_explain_routine_eli5_calls_claude(mock_lookup, mock_anthropic):
    mock_lookup.return_value = {
        "id": 1, "subroutine_name": "DGESV", "routine_type": "driver",
        "file_path": "SRC/dgesv.f", "line_start": 1, "line_end": 100,
        "content": "SUBROUTINE DGESV...", "metadata": {},
        "calls": ["DGETRF", "DGETRS"], "embedding": [0.1] * 1536,
    }

    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.return_value.content = [
        MagicMock(text="Imagine sorting toy blocks into neat piles.")
    ]

    result = explain_routine_eli5("DGESV")
    assert result is not None
    assert result["subroutine_name"] == "DGESV"
    assert "toy blocks" in result["explanation"]
    mock_client.messages.create.assert_called_once()


# --- find_entry_points tests ---

@patch("app.services.understanding.anthropic")
@patch("app.services.understanding._get_conn")
def test_find_entry_points(mock_conn, mock_anthropic):
    cur = MagicMock()
    cur.fetchall.return_value = [
        ("SRC/dgesv.f", 1, 100, "DGESV", "driver", "SUBROUTINE DGESV..."),
        ("SRC/dgels.f", 1, 80, "DGELS", "driver", "SUBROUTINE DGELS..."),
    ]
    mock_conn.return_value.cursor.return_value = cur

    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.return_value.content = [
        MagicMock(text="DGESV solves linear systems. DGELS solves least squares.")
    ]

    result = find_entry_points(top_k=5)
    assert result is not None
    assert result["analysis_type"] == "entry_points"
    assert "DGESV solves" in result["analysis"]
    assert len(result["chunks"]) == 2
    assert result["chunks"][0]["subroutine_name"] == "DGESV"


# --- find_data_usage tests ---

@patch("app.services.understanding.anthropic")
@patch("app.services.understanding._get_conn")
def test_find_data_usage(mock_conn, mock_anthropic):
    cur = MagicMock()
    cur.fetchall.return_value = [
        ("SRC/dgesv.f", 1, 100, "DGESV", "driver", "SUBROUTINE DGESV(N, NRHS, A, LDA, ...)"),
        ("SRC/dgetrf.f", 1, 80, "DGETRF", "computational", "SUBROUTINE DGETRF(M, N, A, LDA, ...)"),
    ]
    mock_conn.return_value.cursor.return_value = cur

    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.return_value.content = [
        MagicMock(text="LDA is used as the leading dimension of array A in both routines.")
    ]

    result = find_data_usage("LDA", top_k=5)
    assert result is not None
    assert result["analysis_type"] == "data_usage"
    assert "LDA" in result["analysis"]
    assert len(result["chunks"]) == 2


# --- find_io_operations tests ---

@patch("app.services.understanding.anthropic")
@patch("app.services.understanding._get_conn")
def test_find_io_operations(mock_conn, mock_anthropic):
    cur = MagicMock()
    cur.fetchall.return_value = [
        ("SRC/xerbla.f", 1, 50, "XERBLA", "computational", "SUBROUTINE XERBLA\n      WRITE(*,*) 'Error'"),
    ]
    mock_conn.return_value.cursor.return_value = cur

    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.return_value.content = [
        MagicMock(text="XERBLA uses WRITE to output error messages to stdout.")
    ]

    result = find_io_operations(top_k=5)
    assert result is not None
    assert result["analysis_type"] == "io_operations"
    assert "WRITE" in result["analysis"]
    assert len(result["chunks"]) == 1


# --- find_error_patterns tests ---

@patch("app.services.understanding.anthropic")
@patch("app.services.understanding._get_conn")
def test_find_error_patterns(mock_conn, mock_anthropic):
    cur = MagicMock()
    cur.fetchall.return_value = [
        ("SRC/dgesv.f", 1, 100, "DGESV", "driver",
         "SUBROUTINE DGESV\n      IF (INFO.NE.0) THEN\n        CALL XERBLA('DGESV', -INFO)\n      END IF"),
    ]
    mock_conn.return_value.cursor.return_value = cur

    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.return_value.content = [
        MagicMock(text="DGESV uses XERBLA for parameter validation and INFO for error status.")
    ]

    result = find_error_patterns(top_k=5)
    assert result is not None
    assert result["analysis_type"] == "error_patterns"
    assert "XERBLA" in result["analysis"]
    assert len(result["chunks"]) == 1
