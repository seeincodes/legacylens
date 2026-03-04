# backend/tests/test_retrieval.py
import sys, os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.retrieval import (
    reciprocal_rank_fusion, normalize_scores, expand_query, keyword_search,
    concept_boost, llm_rerank,
)


def test_rrf_merges_two_result_lists():
    vector_results = [
        {"id": 1, "score": 0.95},
        {"id": 2, "score": 0.85},
        {"id": 3, "score": 0.75},
    ]
    keyword_results = [
        {"id": 2, "score": 10.5},
        {"id": 4, "score": 8.2},
        {"id": 1, "score": 6.1},
    ]
    merged = reciprocal_rank_fusion(vector_results, keyword_results, k=60)
    ids = [r["id"] for r in merged]
    # IDs that appear in both lists should rank highest
    assert ids[0] in (1, 2)
    assert len(merged) == 4  # 4 unique IDs


def test_rrf_handles_empty_keyword_results():
    vector_results = [{"id": 1, "score": 0.9}]
    merged = reciprocal_rank_fusion(vector_results, [], k=60)
    assert len(merged) == 1
    assert merged[0]["id"] == 1


def test_rrf_handles_empty_vector_results():
    keyword_results = [{"id": 5, "score": 3.0}]
    merged = reciprocal_rank_fusion([], keyword_results, k=60)
    assert len(merged) == 1
    assert merged[0]["id"] == 5


def test_rrf_preserves_all_fields():
    vector_results = [{"id": 1, "score": 0.9, "file_path": "SRC/dgesv.f", "content": "test"}]
    merged = reciprocal_rank_fusion(vector_results, [], k=60)
    assert merged[0]["file_path"] == "SRC/dgesv.f"
    assert merged[0]["content"] == "test"
    assert "rrf_score" in merged[0]


def test_normalize_scores_best_result_is_one():
    merged = [
        {"id": 1, "rrf_score": 0.033},
        {"id": 2, "rrf_score": 0.020},
        {"id": 3, "rrf_score": 0.010},
    ]
    normalized = normalize_scores(merged)
    assert normalized[0]["rrf_score"] == 1.0
    assert abs(normalized[1]["rrf_score"] - 0.020 / 0.033) < 0.01
    assert abs(normalized[2]["rrf_score"] - 0.010 / 0.033) < 0.01


def test_normalize_scores_single_result():
    merged = [{"id": 1, "rrf_score": 0.016}]
    normalized = normalize_scores(merged)
    assert normalized[0]["rrf_score"] == 1.0


def test_normalize_scores_empty_list():
    assert normalize_scores([]) == []


def test_normalize_scores_adds_relevance_label():
    merged = [
        {"id": 1, "rrf_score": 0.033},
        {"id": 2, "rrf_score": 0.020},
        {"id": 3, "rrf_score": 0.005},
    ]
    normalized = normalize_scores(merged)
    assert normalized[0]["relevance_label"] == "High"
    assert normalized[1]["relevance_label"] == "Medium"
    assert normalized[2]["relevance_label"] == "Low"


def test_expand_query_returns_original_plus_variants():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(type="text", text="LU factorization solver\nAx=b linear system computation")]

    with patch("app.services.retrieval.anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_client.messages.create.return_value = mock_response

        variants = expand_query("solve linear system")

    assert "solve linear system" in variants
    assert len(variants) >= 2
    assert len(variants) <= 4


def test_expand_query_handles_api_error_gracefully():
    with patch("app.services.retrieval.anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API error")

        variants = expand_query("solve linear system")

    assert variants == ["solve linear system"]


def test_keyword_search_boosts_exact_name_match():
    """keyword_search SQL should include subroutine name matching, not just FTS."""
    import inspect
    source = inspect.getsource(keyword_search)
    # The SQL should reference subroutine_name for boosting
    assert "subroutine_name" in source
    # Should have a CASE or similar boosting expression
    assert "CASE" in source.upper() or "UNION" in source.upper()


def test_concept_boost_injects_matching_routine():
    """concept_boost should inject D-prefix routines for concept matches."""
    mock_row = (42, "SRC/dpotrf.f", 1, 100, "DPOTRF", "computational",
                "SUBROUTINE DPOTRF", {"calls": ["DPOTF2"]})

    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = mock_row

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch("app.db.get_connection") as mock_get_conn:
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

        existing = [{"id": 1, "subroutine_name": "SPOTRF", "rrf_score": 0.02}]
        result = concept_boost("Cholesky factorization", existing)

    # Should have injected DPOTRF with a very high score
    dpotrf_results = [r for r in result if r.get("subroutine_name") == "DPOTRF"]
    assert len(dpotrf_results) >= 1
    assert dpotrf_results[0]["rrf_score"] >= 999.0


def test_concept_boost_no_match_passes_through():
    """concept_boost should return original results for non-matching queries."""
    existing = [{"id": 1, "subroutine_name": "DGESV", "rrf_score": 0.02}]
    # "What does DGESV do?" has no concept match
    result = concept_boost("What does DGESV do?", existing)
    assert result == existing


def test_concept_boost_boosts_existing_result():
    """concept_boost should add score to existing results that match concepts."""
    mock_row = (1, "SRC/dpotrf.f", 1, 100, "DPOTRF", "computational",
                "SUBROUTINE DPOTRF", {"calls": []})

    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = mock_row

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch("app.db.get_connection") as mock_get_conn:
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

        existing = [{"id": 1, "subroutine_name": "DPOTRF", "rrf_score": 0.02}]
        result = concept_boost("Cholesky factorization", existing)

    # Existing result should have boosted score (multiple concept entries may match)
    assert result[0]["rrf_score"] >= 999.0


def test_llm_rerank_success():
    """llm_rerank should reorder candidates based on LLM response."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="2,0,1")]

    with patch("app.services.retrieval.anthropic") as mock_anthropic, \
         patch("app.services.retrieval._get_anthropic_client") as mock_get_client:
        mock_anthropic.__bool__ = MagicMock(return_value=True)
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.messages.create.return_value = mock_response

        candidates = [
            {"id": 1, "subroutine_name": "A", "content": "* desc A\n", "routine_type": "comp"},
            {"id": 2, "subroutine_name": "B", "content": "* desc B\n", "routine_type": "comp"},
            {"id": 3, "subroutine_name": "C", "content": "* desc C\n", "routine_type": "comp"},
        ]
        result = llm_rerank("test query", candidates, top_k=3)

    assert result[0]["id"] == 3  # index 2
    assert result[1]["id"] == 1  # index 0
    assert result[2]["id"] == 2  # index 1


def test_llm_rerank_fallback_on_error():
    """llm_rerank should return original order on API failure."""
    with patch("app.services.retrieval.anthropic") as mock_anthropic, \
         patch("app.services.retrieval._get_anthropic_client") as mock_get_client:
        mock_anthropic.__bool__ = MagicMock(return_value=True)
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API error")

        candidates = [
            {"id": 1, "subroutine_name": "A", "content": "", "routine_type": "comp"},
            {"id": 2, "subroutine_name": "B", "content": "", "routine_type": "comp"},
        ]
        result = llm_rerank("test query", candidates, top_k=2)

    assert result[0]["id"] == 1
    assert result[1]["id"] == 2


def test_llm_rerank_no_anthropic():
    """llm_rerank should return truncated list when anthropic is None."""
    with patch("app.services.retrieval.anthropic", None):
        candidates = [{"id": i} for i in range(10)]
        result = llm_rerank("test", candidates, top_k=5)
    assert len(result) == 5
