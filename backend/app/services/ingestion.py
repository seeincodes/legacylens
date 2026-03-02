import os
import re
from pathlib import Path

import psycopg2
import psycopg2.extras

SUBROUTINE_RE = re.compile(
    r"^\s+(SUBROUTINE|(?:[\w*]+\s+)?FUNCTION)\s+(\w+)\s*\(",
    re.MULTILINE | re.IGNORECASE,
)
END_RE = re.compile(
    r"^\s+END\s*(SUBROUTINE|FUNCTION)?\s*(\w*)\s*$",
    re.MULTILINE | re.IGNORECASE,
)
CALL_RE = re.compile(r"CALL\s+(\w+)", re.IGNORECASE)
PRECISION_MAP = {"s": "single", "d": "double", "c": "complex", "z": "double_complex"}


def detect_precision(file_path: str) -> str:
    basename = Path(file_path).stem.lower()
    if basename and basename[0] in PRECISION_MAP:
        return PRECISION_MAP[basename[0]]
    return "unknown"


def detect_routine_type(content: str, file_path: str) -> str:
    if "blas" in file_path.lower():
        return "blas"
    upper = content.upper()
    if upper.count("CALL ") >= 3:
        return "driver"
    return "computational"


def extract_metadata(content: str, file_path: str) -> dict:
    calls = list(set(m.group(1).upper() for m in CALL_RE.finditer(content)))
    return {
        "file_path": file_path,
        "precision_type": detect_precision(file_path),
        "routine_type": detect_routine_type(content, file_path),
        "calls": calls,
    }


def parse_fortran_file(content: str, file_path: str) -> list[dict]:
    meta = extract_metadata(content, file_path)
    lines = content.split("\n")
    chunks = []
    current_name = None
    current_start = 0

    for i, line in enumerate(lines):
        sub_match = SUBROUTINE_RE.match(line)
        if sub_match:
            current_name = sub_match.group(2).upper()
            current_start = i

        end_match = END_RE.match(line)
        if end_match and current_name:
            # Include preceding comment block
            comment_start = current_start
            for j in range(current_start - 1, -1, -1):
                stripped = lines[j].strip()
                if stripped.startswith("*") or stripped.startswith("!") or stripped == "":
                    comment_start = j
                else:
                    break
            if comment_start < current_start:
                current_start = comment_start

            chunk_content = "\n".join(lines[current_start : i + 1])
            chunks.append({
                "file_path": file_path,
                "line_start": current_start + 1,
                "line_end": i + 1,
                "subroutine_name": current_name,
                "routine_type": meta["routine_type"],
                "precision_type": meta["precision_type"],
                "content": chunk_content,
                "metadata": {"calls": meta["calls"]},
            })
            current_name = None

    if not chunks:
        basename = Path(file_path).stem.upper()
        chunks.append({
            "file_path": file_path,
            "line_start": 1,
            "line_end": len(lines),
            "subroutine_name": basename,
            "routine_type": meta["routine_type"],
            "precision_type": meta["precision_type"],
            "content": content,
            "metadata": {"calls": meta["calls"]},
        })

    return chunks


def discover_fortran_files(base_dir: str) -> list[str]:
    files = []
    for root, _, filenames in os.walk(base_dir):
        for f in filenames:
            if f.endswith((".f", ".f90")):
                files.append(os.path.join(root, f))
    return sorted(files)


def build_chunk_text(chunk: dict) -> str:
    prefix = (
        f"File: {chunk['file_path']} | "
        f"Subroutine: {chunk['subroutine_name']} | "
        f"Type: {chunk['routine_type']} | "
        f"Precision: {chunk['precision_type']}"
    )
    return f"{prefix}\n\n{chunk['content']}"


def generate_embeddings(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    import openai
    from app.config import settings
    client = openai.OpenAI(api_key=settings.openai_api_key)
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(model="text-embedding-3-small", input=batch)
        all_embeddings.extend([item.embedding for item in response.data])
        print(f"  Embedded {min(i + batch_size, len(texts))}/{len(texts)}")
    return all_embeddings


def store_chunks(chunks: list[dict], embeddings: list[list[float]]):
    from pgvector.psycopg2 import register_vector
    from app.config import settings
    conn = psycopg2.connect(settings.database_url)
    register_vector(conn)
    cur = conn.cursor()
    for chunk, emb in zip(chunks, embeddings):
        cur.execute(
            """INSERT INTO code_chunks
                (file_path, line_start, line_end, subroutine_name,
                 routine_type, precision_type, content, metadata, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (chunk["file_path"], chunk["line_start"], chunk["line_end"],
             chunk["subroutine_name"], chunk["routine_type"], chunk["precision_type"],
             chunk["content"], psycopg2.extras.Json(chunk["metadata"]), emb),
        )
    conn.commit()
    cur.close()
    conn.close()
