import re

import anthropic

from app.config import settings
from app.models.schemas import ChunkResult

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


SYSTEM_PROMPT = """You are a legacy code expert analyzing Fortran source code from the LAPACK library.

You are given numbered code snippets retrieved from the codebase. Answer the user's question using ONLY these snippets.

Rules:
- ONLY cite file paths and line numbers that appear in the provided snippets — never invent references
- Use the format [file_path:line_start-line_end] exactly as shown in each result header
- Explain what the code does in plain English
- Mention related routines the user might want to explore
- If the provided snippets don't contain enough information to answer, say so explicitly
- Be concise but thorough"""

BRIEF_SYSTEM_PROMPT = """You are a legacy code expert analyzing Fortran source from LAPACK.

Answer the user's question in 1-3 sentences. Be concise. Use ONLY the provided code snippets.
ALWAYS cite your source: include [file_path:line_start-line_end] for each snippet you use (e.g. [SRC/dgesv.f:1-158])."""

_REF_PATTERN = re.compile(r"\[([^\]]+?):(\d+)(?:-(\d+))?\]")


def _normalize_path(p: str) -> str:
    return p.replace("\\", "/").strip()


def _ref_is_valid(file_path: str, line_a: int, line_b: int | None, chunks: list[ChunkResult]) -> bool:
    """Check if citation (file, line_a, line_b) overlaps any chunk's range."""
    norm_cited = _normalize_path(file_path)
    line_end = line_b if line_b is not None else line_a

    for c in chunks:
        if _normalize_path(c.file_path) != norm_cited:
            continue
        # Cited range [line_a, line_end] overlaps chunk [c.line_start, c.line_end]
        if line_a <= c.line_end and line_end >= c.line_start:
            return True
    return False


def validate_references(answer: str, chunks: list[ChunkResult]) -> tuple[str, bool]:
    """Validate file:line refs against chunks. Returns (answer, has_unverified)."""
    has_unverified = False

    def _check_ref(match):
        nonlocal has_unverified
        file_path = match.group(1)
        line_a = int(match.group(2))
        line_b = int(match.group(3)) if match.group(3) else None
        if _ref_is_valid(file_path, line_a, line_b, chunks):
            return match.group(0)
        has_unverified = True
        return f"{match.group(0)} (unverified)"

    result = _REF_PATTERN.sub(_check_ref, answer)
    return result, has_unverified


def build_context(chunks: list[ChunkResult]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"--- Result {i}: {chunk.file_path}:{chunk.line_start}-{chunk.line_end} "
            f"(Subroutine: {chunk.subroutine_name}, Type: {chunk.routine_type}) ---\n"
            f"{chunk.content}\n"
        )
    return "\n".join(parts)


def generate_answer(query: str, chunks: list[ChunkResult], brief: bool = False) -> str:
    client = _get_client()
    context = build_context(chunks)
    system = BRIEF_SYSTEM_PROMPT if brief else SYSTEM_PROMPT
    max_tokens = 256 if brief else 1024
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": f"Retrieved code context:\n\n{context}\n\nQuestion: {query}"}],
    )
    answer = message.content[0].text
    answer, _ = validate_references(answer, chunks)
    return answer


async def stream_answer(query: str, chunks: list[ChunkResult], brief: bool = False):
    client = _get_client()
    context = build_context(chunks)
    system = BRIEF_SYSTEM_PROMPT if brief else SYSTEM_PROMPT
    max_tokens = 256 if brief else 1024
    with client.messages.stream(
        model="claude-haiku-4-5-20251001",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": f"Retrieved code context:\n\n{context}\n\nQuestion: {query}"}],
    ) as stream:
        for text in stream.text_stream:
            yield text
