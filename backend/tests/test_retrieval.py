# backend/tests/test_retrieval.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.retrieval import reciprocal_rank_fusion


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
