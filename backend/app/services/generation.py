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

_REF_PATTERN = re.compile(r"\[([^\]]+?):(\d+)(?:-(\d+))?\]")


def validate_references(answer: str, chunks: list[ChunkResult]) -> str:
    """Strip or flag file:line references not found in provided chunks."""
    valid_files = {c.file_path for c in chunks}

    def _check_ref(match):
        file_path = match.group(1)
        if file_path in valid_files:
            return match.group(0)
        return f"{match.group(0)} (unverified)"

    return _REF_PATTERN.sub(_check_ref, answer)


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
    client = _get_client()
    context = build_context(chunks)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Retrieved code context:\n\n{context}\n\nQuestion: {query}"}],
    )
    answer = message.content[0].text
    return validate_references(answer, chunks)


async def stream_answer(query: str, chunks: list[ChunkResult]):
    client = _get_client()
    context = build_context(chunks)
    with client.messages.stream(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Retrieved code context:\n\n{context}\n\nQuestion: {query}"}],
    ) as stream:
        for text in stream.text_stream:
            yield text
