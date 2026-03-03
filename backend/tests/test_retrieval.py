# backend/tests/test_retrieval.py
import sys, os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.retrieval import reciprocal_rank_fusion, normalize_scores, expand_query, keyword_search


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
