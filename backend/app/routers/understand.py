from fastapi import APIRouter, HTTPException

from app.models.understand_schemas import (
    ExplainRequest, ExplainResponse,
    ELI5Request, ELI5Response,
    DependencyRequest, DependencyResponse,
    SimilarRequest, SimilarResponse,
    DocumentRequest, DocumentResponse,
    EntryPointsRequest, DataUsageRequest, IoOperationsRequest, ErrorPatternsRequest,
    AnalysisResponse,
)
from app.services.understanding import (
    explain_routine,
    explain_routine_eli5,
    build_dependency_graph,
    find_similar_routines,
    generate_documentation,
    find_entry_points,
    find_data_usage,
    find_io_operations,
    find_error_patterns,
)

router = APIRouter(prefix="/understand", tags=["understand"])


@router.post("/explain", response_model=ExplainResponse)
async def explain(request: ExplainRequest):
    """Explain a subroutine in plain English."""
    result = explain_routine(request.subroutine_name)
    if not result:
        raise HTTPException(status_code=404, detail=f"Routine '{request.subroutine_name}' not found")
    return result


@router.post("/eli5", response_model=ELI5Response)
async def eli5(request: ELI5Request):
    """Explain a subroutine in kid-friendly ELI5 language."""
    result = explain_routine_eli5(request.subroutine_name)
    if not result:
        raise HTTPException(status_code=404, detail=f"Routine '{request.subroutine_name}' not found")
    return result


@router.post("/dependencies", response_model=DependencyResponse)
async def dependencies(request: DependencyRequest):
    """Trace the call chain of a subroutine via BFS."""
    result = build_dependency_graph(request.subroutine_name, max_depth=request.max_depth)
    if not result:
        raise HTTPException(status_code=404, detail=f"Routine '{request.subroutine_name}' not found")
    return result


@router.post("/similar", response_model=SimilarResponse)
async def similar(request: SimilarRequest):
    """Find routines with similar embeddings."""
    result = find_similar_routines(request.subroutine_name, top_k=request.top_k)
    if not result:
        raise HTTPException(status_code=404, detail=f"Routine '{request.subroutine_name}' not found")
    return result


@router.post("/document", response_model=DocumentResponse)
async def document(request: DocumentRequest):
    """Generate structured documentation for a subroutine."""
    result = generate_documentation(request.subroutine_name)
    if not result:
        raise HTTPException(status_code=404, detail=f"Routine '{request.subroutine_name}' not found")
    return result


@router.post("/entry-points", response_model=AnalysisResponse)
async def entry_points(request: EntryPointsRequest):
    """Find and summarize driver routines (main entry points)."""
    return find_entry_points(top_k=request.top_k)


@router.post("/data-usage", response_model=AnalysisResponse)
async def data_usage(request: DataUsageRequest):
    """Find routines that reference a given variable or parameter."""
    return find_data_usage(request.variable_name, top_k=request.top_k)


@router.post("/io-operations", response_model=AnalysisResponse)
async def io_operations(request: IoOperationsRequest):
    """Find file I/O operations across the codebase."""
    return find_io_operations(top_k=request.top_k)


@router.post("/error-patterns", response_model=AnalysisResponse)
async def error_patterns(request: ErrorPatternsRequest):
    """Find and categorize error handling patterns."""
    return find_error_patterns(top_k=request.top_k)
