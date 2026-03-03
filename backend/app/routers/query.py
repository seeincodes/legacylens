import json
import logging
import os
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.models.schemas import QueryRequest, QueryResponse
from app.services.retrieval import search
from app.services.generation import generate_answer, stream_answer

logger = logging.getLogger("legacylens.query")

router = APIRouter()
REPO_ROOT = Path(__file__).resolve().parents[3]
LAPACK_BASE_DIR = (REPO_ROOT / "data" / "lapack").resolve()


def _resolve_lapack_file(file_path: str) -> Path | None:
    raw = file_path.strip().replace("\\", "/")
    if raw.startswith("file://"):
        raw = raw[len("file://"):]

    candidates: list[Path] = []

    # Absolute path input from older ingestions or alternate metadata formats.
    if Path(raw).is_absolute():
        candidates.append(Path(raw))

    # Raw relative path directly under data/lapack.
    candidates.append(LAPACK_BASE_DIR / raw.lstrip("/"))

    for prefix in ("data/lapack/", "lapack/"):
        if raw.startswith(prefix):
            candidates.append(LAPACK_BASE_DIR / raw[len(prefix):])

    for marker in ("BLAS/SRC/", "SRC/"):
        idx = raw.find(marker)
        if idx != -1:
            candidates.append(LAPACK_BASE_DIR / raw[idx:])

    seen: set[str] = set()
    base = str(LAPACK_BASE_DIR)
    for candidate in candidates:
        resolved = candidate.resolve()
        resolved_str = str(resolved)
        if resolved_str in seen:
            continue
        seen.add(resolved_str)

        # Prevent path traversal: only serve files inside data/lapack.
        if os.path.commonpath([base, resolved_str]) != base:
            continue
        if resolved.is_file():
            return resolved
    return None


def _read_file_response(file_path: str) -> dict:
    resolved = _resolve_lapack_file(file_path)
    if resolved is None:
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    with open(resolved, "r", errors="replace") as f:
        content = f.read()

    rel_path = str(resolved.relative_to(LAPACK_BASE_DIR))
    return {"file_path": rel_path, "content": content}


@router.post("/query")
async def query_codebase(request: QueryRequest):
    """Main query endpoint -- retrieves code and streams LLM answer."""
    t_start = time.perf_counter()
    chunks = search(
        query=request.query,
        top_k=request.top_k,
        routine_type=request.routine_type,
        precision_type=request.precision_type,
        expand=request.expand,
    )
    retrieval_ms = (time.perf_counter() - t_start) * 1000
    routines = [c.subroutine_name for c in chunks if c.subroutine_name]
    logger.info(
        "query=%r retrieval_ms=%.0f top_k=%d expand=%s results=%d routines=%s",
        request.query, retrieval_ms, request.top_k, request.expand, len(chunks), routines,
    )

    async def event_stream():
        yield f"data: {json.dumps({'type': 'chunks', 'chunks': [c.model_dump() for c in chunks]})}\n\n"
        t_gen = time.perf_counter()
        full_answer = ""
        async for token in stream_answer(request.query, chunks):
            full_answer += token
            yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"
        generation_ms = (time.perf_counter() - t_gen) * 1000
        total_ms = (time.perf_counter() - t_start) * 1000
        yield f"data: {json.dumps({'type': 'done', 'answer': full_answer})}\n\n"
        logger.info(
            "query=%r generation_ms=%.0f total_ms=%.0f",
            request.query, generation_ms, total_ms,
        )

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/query/sync")
async def query_codebase_sync(request: QueryRequest) -> QueryResponse:
    """Non-streaming version for testing."""
    chunks = search(
        query=request.query,
        top_k=request.top_k,
        routine_type=request.routine_type,
        precision_type=request.precision_type,
        expand=request.expand,
    )
    answer = generate_answer(request.query, chunks)
    return QueryResponse(answer=answer, chunks=chunks)


@router.get("/file")
async def get_file_by_query(path: str = Query(..., alias="path")):
    """Return full file content using query param to avoid path encoding issues."""
    return _read_file_response(path)


@router.get("/file/{file_path:path}")
async def get_file(file_path: str):
    """Return full file content for drill-down view."""
    return _read_file_response(file_path)
