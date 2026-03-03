import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch, MagicMock
from app.services.understanding import build_dependency_graph, lookup_routine, explain_routine


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
