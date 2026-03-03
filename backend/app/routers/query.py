import json
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import QueryRequest, QueryResponse
from app.services.retrieval import search
from app.services.generation import generate_answer, stream_answer

router = APIRouter()


@router.post("/query")
async def query_codebase(request: QueryRequest):
    """Main query endpoint -- retrieves code and streams LLM answer."""
    chunks = search(
        query=request.query,
        top_k=request.top_k,
        routine_type=request.routine_type,
        precision_type=request.precision_type,
        expand=request.expand,
    )

    async def event_stream():
        yield f"data: {json.dumps({'type': 'chunks', 'chunks': [c.model_dump() for c in chunks]})}\n\n"
        full_answer = ""
        async for token in stream_answer(request.query, chunks):
            full_answer += token
            yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'answer': full_answer})}\n\n"

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


@router.get("/file/{file_path:path}")
async def get_file(file_path: str):
    """Return full file content for drill-down view."""
    base_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "lapack")
    full_path = os.path.join(base_dir, file_path)
    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    with open(full_path, "r", errors="replace") as f:
        content = f.read()
    return {"file_path": file_path, "content": content}
