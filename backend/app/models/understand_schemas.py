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


class TranslateRequest(BaseModel):
    subroutine_name: str


class UseCasesRequest(BaseModel):
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
    corrected_from: str | None = None


class ELI5Response(BaseModel):
    subroutine_name: str
    routine_type: str | None
    file_path: str
    line_start: int
    line_end: int
    explanation: str
    calls: list[str]
    corrected_from: str | None = None


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
    corrected_from: str | None = None


class SimilarRoutine(BaseModel):
    subroutine_name: str | None
    routine_type: str | None
    file_path: str
    relevance_score: float
    content_preview: str


class SimilarResponse(BaseModel):
    subroutine_name: str
    similar: list[SimilarRoutine]
    corrected_from: str | None = None


class DocumentResponse(BaseModel):
    subroutine_name: str
    documentation: str
    corrected_from: str | None = None


class TranslateResponse(BaseModel):
    subroutine_name: str
    code: str
    explanation: str
    corrected_from: str | None = None


class UseCasesResponse(BaseModel):
    subroutine_name: str
    use_cases: str
    typical_callers: list[str] = []
    corrected_from: str | None = None
