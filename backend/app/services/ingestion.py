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
BRIEF_RE = re.compile(r'\*>\s*\\brief\s*<b>\s*(.*?)</b>', re.IGNORECASE)
PURPOSE_RE = re.compile(r'\*>\s*\\verbatim\s*\n((?:\*>.*\n)*)', re.MULTILINE)
HTMLONLY_RE = re.compile(r'\*>\s*\\htmlonly.*?\\endhtmlonly\s*\n?', re.DOTALL)
DOC_BANNER_RE = re.compile(r'\*\s*=+\s*DOCUMENTATION\s*=+\s*\n(?:\*\s*\n)*', re.IGNORECASE)
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


def extract_description(content: str) -> str:
    """Extract a human-readable description from Fortran comment headers.

    Tries two patterns:
    1. \\brief <b> ROUTINE description text </b>  -- strip the routine name prefix
    2. If \\brief only has the routine name, look in the Purpose/\\verbatim section
    """
    # Pattern A: description inside \brief <b>...</b>
    m = BRIEF_RE.search(content)
    if m:
        raw = m.group(1).strip()
        # Check if this is more than just a routine name (e.g. "DPOTRF" vs
        # "DGESV computes the solution ...").  A bare name is a single word
        # with no spaces beyond leading/trailing whitespace.
        if " " in raw:
            # Strip leading routine name if present (e.g. "DGESV computes..." -> "computes...")
            # The routine name is typically the first all-caps token.
            tokens = raw.split(None, 1)
            if len(tokens) == 2 and tokens[0].isupper():
                return tokens[1].strip()
            return raw
        # Fall through to Pattern B if brief only contains the routine name.

    # Pattern B: description in Purpose / \verbatim block
    m = PURPOSE_RE.search(content)
    if m:
        block = m.group(1)
        # Clean up Fortran comment markers and collect non-empty lines
        lines: list[str] = []
        for line in block.splitlines():
            # Strip the leading "*>" marker
            cleaned = re.sub(r'^\s*\*>\s?', '', line).strip()
            if cleaned:
                lines.append(cleaned)
        if lines:
            text = " ".join(lines)
            # Remove stray Doxygen markers
            text = text.replace("\\endverbatim", "").replace("\\verbatim", "")
            # Collapse whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            # Truncate to first 200 chars at a word boundary
            if len(text) > 200:
                text = text[:200].rsplit(' ', 1)[0]
            return text

    return ""


def strip_html_noise(content: str) -> str:
    """Remove \\htmlonly...\\endhtmlonly blocks and the DOCUMENTATION banner."""
    result = HTMLONLY_RE.sub('', content)
    result = DOC_BANNER_RE.sub('', result)
    return result


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
                "metadata": {"calls": list(set(
                    m.group(1).upper() for m in CALL_RE.finditer(chunk_content)
                ))},
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
            if f.endswith((".f", ".f90", ".f95", ".f03")):
                files.append(os.path.join(root, f))
    return sorted(files)


def build_chunk_text(chunk: dict) -> str:
    from app.services.concept_map import get_concepts_for_stem, get_stem_from_routine_name

    desc = extract_description(chunk["content"])
    clean_content = strip_html_noise(chunk["content"])

    prefix_parts = [
        f"File: {chunk['file_path']}",
        f"Subroutine: {chunk['subroutine_name']}",
        f"Type: {chunk['routine_type']}",
        f"Precision: {chunk['precision_type']}",
    ]
    if desc:
        prefix_parts.append(f"Description: {desc}")

    name = chunk.get("subroutine_name") or ""
    stem = get_stem_from_routine_name(name)
    concepts = get_concepts_for_stem(stem)
    if concepts:
        prefix_parts.append(f"Concepts: {', '.join(concepts)}")

    prefix = " | ".join(prefix_parts)
    return f"{prefix}\n\n{clean_content}"


def generate_embeddings(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    import time
    import openai
    from app.config import settings
    client = openai.OpenAI(api_key=settings.openai_api_key)
    # Truncate texts that exceed the model's 8191 token limit (~4 chars/token for code)
    max_chars = 10000
    texts = [t[:max_chars] if len(t) > max_chars else t for t in texts]
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        for attempt in range(5):
            try:
                response = client.embeddings.create(model="text-embedding-3-small", input=batch)
                all_embeddings.extend([item.embedding for item in response.data])
                break
            except openai.RateLimitError as e:
                wait = 2 ** attempt + 1
                print(f"  Rate limited, waiting {wait}s... ({e})")
                time.sleep(wait)
        else:
            raise RuntimeError(f"Failed to embed batch {i} after 5 retries")
        print(f"  Embedded {min(i + batch_size, len(texts))}/{len(texts)}")
    return all_embeddings


def store_chunks(chunks: list[dict], embeddings: list[list[float]]):
    from pgvector.psycopg2 import register_vector
    from app.config import settings
    conn = psycopg2.connect(settings.database_url)
    register_vector(conn)
    cur = conn.cursor()
    sql = """INSERT INTO code_chunks
                (file_path, line_start, line_end, subroutine_name,
                 routine_type, precision_type, content, metadata, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
    data = [
        (chunk["file_path"], chunk["line_start"], chunk["line_end"],
         chunk["subroutine_name"], chunk["routine_type"], chunk["precision_type"],
         chunk["content"], psycopg2.extras.Json(chunk["metadata"]), emb)
        for chunk, emb in zip(chunks, embeddings)
    ]
    psycopg2.extras.execute_batch(cur, sql, data, page_size=100)
    conn.commit()
    cur.close()
    conn.close()
