from fastapi import APIRouter
from app.models.schemas import QueryRequest

router = APIRouter()


@router.post("/query")
async def query_codebase(request: QueryRequest):
    return {"answer": "Not implemented yet", "chunks": []}
