from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    routine_type: str | None = None
    precision_type: str | None = None
    blas_level: str | None = None
    expand: bool = False
    rerank: bool = True
    brief: bool = False


class ChunkResult(BaseModel):
    file_path: str
    line_start: int
    line_end: int
    subroutine_name: str | None
    routine_type: str | None
    blas_level: str | None = None
    content: str
    relevance_score: float
    relevance_label: str = "Medium"
    similarity_score: float = 0.0
    calls: list[str] | None = None


class QueryResponse(BaseModel):
    answer: str
    chunks: list[ChunkResult]
