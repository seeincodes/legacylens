import anthropic

from app.config import settings
from app.models.schemas import ChunkResult

SYSTEM_PROMPT = """You are a legacy code expert analyzing Fortran source code from the LAPACK library (Linear Algebra PACKage). Given code snippets retrieved from the codebase, answer the user's question.

Rules:
- Always cite specific file paths and line numbers in [file:line] format
- Explain what the code does in plain English
- Mention related routines the user might want to explore
- Be concise but thorough"""


def build_context(chunks: list[ChunkResult]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"--- Result {i}: {chunk.file_path}:{chunk.line_start}-{chunk.line_end} "
            f"(Subroutine: {chunk.subroutine_name}, Type: {chunk.routine_type}) ---\n"
            f"{chunk.content}\n"
        )
    return "\n".join(parts)


def generate_answer(query: str, chunks: list[ChunkResult]) -> str:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    context = build_context(chunks)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Retrieved code context:\n\n{context}\n\nQuestion: {query}"}],
    )
    return message.content[0].text


async def stream_answer(query: str, chunks: list[ChunkResult]):
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    context = build_context(chunks)
    with client.messages.stream(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Retrieved code context:\n\n{context}\n\nQuestion: {query}"}],
    ) as stream:
        for text in stream.text_stream:
            yield text


def classify_query(query: str) -> str:
    """Classify a query into an analysis type or 'general'."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=20,
        system=(
            "Classify the user's query about a Fortran/LAPACK codebase into exactly one category. "
            "Respond with ONLY the category name, nothing else.\n\n"
            "Categories:\n"
            "- entry_points: Questions about main entry points, driver routines, where to start\n"
            "- data_usage: Questions about what functions use/modify a specific variable or data structure\n"
            "- io_operations: Questions about file I/O, reading, writing, printing\n"
            "- error_patterns: Questions about error handling, validation, error reporting\n"
            "- general: Everything else (explanations, algorithms, specific routines, etc.)"
        ),
        messages=[{"role": "user", "content": query}],
    )
    category = message.content[0].text.strip().lower()
    valid = {"entry_points", "data_usage", "io_operations", "error_patterns", "general"}
    return category if category in valid else "general"
