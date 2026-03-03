from pydantic import BaseModel


# --- Request models ---

class ExplainRequest(BaseModel):
    subroutine_name: str


class ELI5Request(BaseModel):
    subroutine_name: str


class DependencyRequest(BaseModel):
    subroutine_name: str
    max_depth: int = 3


class SimilarRequest(BaseModel):
    subroutine_name: str
    top_k: int = 5


class DocumentRequest(BaseModel):
    subroutine_name: str


# --- Response models ---

class ExplainResponse(BaseModel):
    subroutine_name: str
    routine_type: str | None
    file_path: str
    line_start: int
    line_end: int
    explanation: str
    calls: list[str]


class ELI5Response(BaseModel):
    subroutine_name: str
    routine_type: str | None
    file_path: str
    line_start: int
    line_end: int
    explanation: str
    calls: list[str]


class DependencyNode(BaseModel):
    name: str
    routine_type: str | None
    file_path: str | None
    calls: list[str]
    depth: int


class DependencyResponse(BaseModel):
    root: str
    nodes: list[DependencyNode]
    max_depth: int


class SimilarRoutine(BaseModel):
    subroutine_name: str | None
    routine_type: str | None
    file_path: str
    relevance_score: float
    content_preview: str


class SimilarResponse(BaseModel):
    subroutine_name: str
    similar: list[SimilarRoutine]


class DocumentResponse(BaseModel):
    subroutine_name: str
    documentation: str


# --- Analysis request models ---

class EntryPointsRequest(BaseModel):
    top_k: int = 10


class DataUsageRequest(BaseModel):
    variable_name: str
    top_k: int = 10


class IoOperationsRequest(BaseModel):
    top_k: int = 10


class ErrorPatternsRequest(BaseModel):
    top_k: int = 10


# --- Analysis response models ---

class AnalysisChunk(BaseModel):
    file_path: str
    subroutine_name: str | None
    content_preview: str


class AnalysisResponse(BaseModel):
    analysis_type: str
    analysis: str
    chunks: list[AnalysisChunk]
