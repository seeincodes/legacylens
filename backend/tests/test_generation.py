import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.generation import build_context
from app.models.schemas import ChunkResult


def test_build_context_formats_chunks():
    chunks = [
        ChunkResult(
            file_path="SRC/dgesv.f", line_start=1, line_end=50,
            subroutine_name="DGESV", routine_type="driver",
            content="SUBROUTINE DGESV(...)", relevance_score=0.95,
        )
    ]
    ctx = build_context(chunks)
    assert "SRC/dgesv.f:1-50" in ctx
    assert "DGESV" in ctx
    assert "SUBROUTINE DGESV" in ctx


def test_build_context_multiple_chunks():
    chunks = [
        ChunkResult(file_path="a.f", line_start=1, line_end=10,
                     subroutine_name="A", routine_type="comp",
                     content="code a", relevance_score=0.9),
        ChunkResult(file_path="b.f", line_start=1, line_end=20,
                     subroutine_name="B", routine_type="comp",
                     content="code b", relevance_score=0.8),
    ]
    ctx = build_context(chunks)
    assert "Result 1" in ctx
    assert "Result 2" in ctx
