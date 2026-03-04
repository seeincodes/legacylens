import json
import re
from collections import OrderedDict

import anthropic
import openai
import psycopg2
from pgvector.psycopg2 import register_vector

from app.config import settings

# ---------------------------------------------------------------------------
# In-memory LRU cache for understand results
# Key: (routine_name_upper, action)  Value: response dict
# ---------------------------------------------------------------------------
_understand_cache: OrderedDict[tuple[str, str], dict] = OrderedDict()
_CACHE_MAX = 512


def _get_cached(name: str, action: str) -> dict | None:
    key = (name.upper(), action)
    if key in _understand_cache:
        _understand_cache.move_to_end(key)
        return _understand_cache[key]
    return None


def _put_cached(name: str, action: str, result: dict) -> None:
    key = (name.upper(), action)
    _understand_cache[key] = result
    _understand_cache.move_to_end(key)
    while len(_understand_cache) > _CACHE_MAX:
        _understand_cache.popitem(last=False)


def _get_conn():
    conn = psycopg2.connect(settings.database_url)
    register_vector(conn)
    return conn


def _truncate_for_llm(content: str, max_chars: int = 6000) -> str:
    """Truncate routine content to reduce tokens and speed up LLM calls."""
    if len(content) <= max_chars:
        return content
    return content[:max_chars] + "\n... [truncated]"


def lookup_routine(name: str, include_embedding: bool = True) -> dict | None:
    """Find a routine by name (case-insensitive). Falls back to fuzzy match on typo.
    Returns dict with all fields or None. Includes corrected_from when fuzzy match was used."""
    conn = _get_conn()
    cur = conn.cursor()
    if include_embedding:
        cur.execute(
            """SELECT id, file_path, line_start, line_end, subroutine_name,
                      routine_type, content, metadata, embedding
               FROM code_chunks
               WHERE subroutine_name ILIKE %s
               LIMIT 1""",
            (name,),
        )
    else:
        cur.execute(
            """SELECT id, file_path, line_start, line_end, subroutine_name,
                      routine_type, content, metadata
               FROM code_chunks
               WHERE subroutine_name ILIKE %s
               LIMIT 1""",
            (name,),
        )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        from app.services.routine_index import fuzzy_match_routine

        corrected = fuzzy_match_routine(name)
        if corrected:
            return lookup_routine(corrected, include_embedding=include_embedding) | {
                "corrected_from": name.strip()
            }
        return None

    meta = row[7] if isinstance(row[7], dict) else (json.loads(row[7]) if row[7] else {})
    out = {
        "id": row[0],
        "file_path": row[1],
        "line_start": row[2],
        "line_end": row[3],
        "subroutine_name": row[4],
        "routine_type": row[5],
        "content": row[6],
        "metadata": meta,
        "calls": meta.get("calls", []),
    }
    if include_embedding:
        out["embedding"] = row[8]
    else:
        out["embedding"] = None
    return out


def _generate_explanation(name: str, system_prompt: str, max_tokens: int = 768) -> dict | None:
    """Look up a routine and generate an explanation via Claude."""
    routine = lookup_routine(name, include_embedding=False)
    if not routine:
        return None

    content = _truncate_for_llm(routine["content"])
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{
            "role": "user",
            "content": (
                f"Subroutine: {routine['subroutine_name']}\n"
                f"File: {routine['file_path']}:{routine['line_start']}-{routine['line_end']}\n"
                f"Type: {routine['routine_type']}\n\n"
                f"```fortran\n{content}\n```"
            ),
        }],
    )

    result = {
        "subroutine_name": routine["subroutine_name"],
        "routine_type": routine["routine_type"],
        "file_path": routine["file_path"],
        "line_start": routine["line_start"],
        "line_end": routine["line_end"],
        "explanation": message.content[0].text,
        "calls": routine["calls"],
    }
    if routine.get("corrected_from"):
        result["corrected_from"] = routine["corrected_from"]
    return result


def explain_routine(name: str) -> dict | None:
    """Look up a routine and generate a plain-English explanation via Claude."""
    cached = _get_cached(name, "explain")
    if cached:
        return cached
    result = _generate_explanation(
        name,
        (
            "You are a Fortran and LAPACK expert. Explain the following subroutine in plain English. "
            "Cover: what it does, its parameters, the algorithm used, and when you'd use it. "
            "Be concise. Keep under 300 words."
        ),
    )
    if result:
        _put_cached(name, "explain", result)
    return result


def explain_routine_eli5(name: str) -> dict | None:
    """Look up a routine and explain it in simple ELI5 language with emoji visuals."""
    cached = _get_cached(name, "eli5")
    if cached:
        return cached
    result = _generate_explanation(
        name,
        (
            "You are a fun, friendly teacher explaining code to a 5-year-old child. "
            "Rules:\n"
            "- Use VERY simple words and SHORT sentences (max 10 words each).\n"
            "- Use lots of emoji as pictures to illustrate concepts (e.g. 🧮 for math, 📦 for storing things, 🔄 for swapping, ✂️ for splitting, 🏗️ for building).\n"
            "- Start with a one-line emoji-rich summary like: '🧮✨ This is like a magic calculator!'\n"
            "- Use a fun real-world analogy a kid would understand (sorting toys, stacking blocks, sharing cookies, etc.).\n"
            "- Break the explanation into small sections with emoji headers.\n"
            "- Never use technical jargon — say 'list of numbers' not 'array', 'answer' not 'return value'.\n"
            "- End with a 'Why do we care?' section explaining why it matters, using kid-friendly examples.\n"
            "- Keep the whole explanation under 200 words."
        ),
        max_tokens=512,
    )
    if result:
        _put_cached(name, "eli5", result)
    return result


def build_dependency_graph(name: str, max_depth: int = 3) -> dict | None:
    """BFS traversal of call chains using metadata.calls."""
    cached = _get_cached(name, f"dependencies:{max_depth}")
    if cached:
        return cached

    root = lookup_routine(name, include_embedding=False)
    if not root:
        return None

    nodes = []
    visited = set()
    queue = [(root["subroutine_name"], root["routine_type"], root["file_path"], root["calls"], 0)]
    visited.add(root["subroutine_name"].upper())

    conn = _get_conn()
    cur = conn.cursor()

    while queue:
        rname, rtype, fpath, calls, depth = queue.pop(0)
        nodes.append({
            "name": rname,
            "routine_type": rtype,
            "file_path": fpath,
            "calls": calls or [],
            "depth": depth,
        })

        if depth >= max_depth or not calls:
            continue

        for callee in calls:
            if callee.upper() in visited:
                continue
            visited.add(callee.upper())

            cur.execute(
                """SELECT subroutine_name, routine_type, file_path, metadata
                   FROM code_chunks
                   WHERE subroutine_name ILIKE %s
                   LIMIT 1""",
                (callee,),
            )
            row = cur.fetchone()
            if row:
                meta = row[3] if isinstance(row[3], dict) else (json.loads(row[3]) if row[3] else {})
                queue.append((row[0], row[1], row[2], meta.get("calls", []), depth + 1))

    cur.close()
    conn.close()

    result = {
        "root": root["subroutine_name"],
        "nodes": nodes,
        "max_depth": max_depth,
    }
    if root.get("corrected_from"):
        result["corrected_from"] = root["corrected_from"]
    _put_cached(name, f"dependencies:{max_depth}", result)
    return result


def find_similar_routines(name: str, top_k: int = 5) -> dict | None:
    """Find routines with similar embeddings, excluding the source routine."""
    cached = _get_cached(name, f"similar:{top_k}")
    if cached:
        return cached

    routine = lookup_routine(name)
    if not routine:
        return None

    embedding = routine["embedding"]
    if embedding is None:
        return {"subroutine_name": routine["subroutine_name"], "similar": []}

    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT file_path, line_start, line_end, subroutine_name, routine_type,
                  content, 1 - (embedding <=> %s::vector) AS score
           FROM code_chunks
           WHERE id != %s
           ORDER BY embedding <=> %s::vector
           LIMIT %s""",
        (embedding, routine["id"], embedding, top_k),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    similar = []
    for r in rows:
        preview = r[5][:200] + "..." if len(r[5]) > 200 else r[5]
        similar.append({
            "subroutine_name": r[3],
            "routine_type": r[4],
            "file_path": r[0],
            "relevance_score": round(float(r[6]), 4),
            "content_preview": preview,
        })

    result = {"subroutine_name": routine["subroutine_name"], "similar": similar}
    if routine.get("corrected_from"):
        result["corrected_from"] = routine["corrected_from"]
    _put_cached(name, f"similar:{top_k}", result)
    return result


def generate_documentation(name: str) -> dict | None:
    """Generate structured documentation for a routine via Claude."""
    cached = _get_cached(name, "document")
    if cached:
        return cached

    routine = lookup_routine(name, include_embedding=False)
    if not routine:
        return None

    content = _truncate_for_llm(routine["content"])
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1536,
        system=(
            "You are a Fortran and LAPACK documentation expert. Generate structured documentation "
            "for the following subroutine. Include these sections:\n"
            "1. PURPOSE - What the routine does\n"
            "2. PARAMETERS - Each parameter with type, intent, and description\n"
            "3. ALGORITHM - Step-by-step explanation of the algorithm\n"
            "4. RETURN VALUES - What INFO values mean\n"
            "5. DEPENDENCIES - Called routines and their roles\n"
            "Format in clean markdown. Be concise."
        ),
        messages=[{
            "role": "user",
            "content": (
                f"Subroutine: {routine['subroutine_name']}\n"
                f"File: {routine['file_path']}:{routine['line_start']}-{routine['line_end']}\n"
                f"Type: {routine['routine_type']}\n"
                f"Calls: {', '.join(routine['calls']) if routine['calls'] else 'None'}\n\n"
                f"```fortran\n{content}\n```"
            ),
        }],
    )

    result = {
        "subroutine_name": routine["subroutine_name"],
        "documentation": message.content[0].text,
    }
    if routine.get("corrected_from"):
        result["corrected_from"] = routine["corrected_from"]
    _put_cached(name, "document", result)
    return result


def translate_routine(name: str) -> dict | None:
    """Generate equivalent NumPy/SciPy code for a routine."""
    cached = _get_cached(name, "translate")
    if cached:
        return cached

    routine = lookup_routine(name, include_embedding=False)
    if not routine:
        return None

    content = _truncate_for_llm(routine["content"])
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1536,
        system=(
            "You are a Fortran and NumPy/SciPy expert. Generate equivalent Python code for the LAPACK routine. "
            "Include: (1) import statements (numpy, scipy.linalg), (2) example usage with sample data, "
            "(3) brief explanation of the mapping (Fortran params → Python args). "
            "Use code blocks with ```python. Be practical and runnable. Be concise."
        ),
        messages=[{
            "role": "user",
            "content": (
                f"Subroutine: {routine['subroutine_name']}\n"
                f"File: {routine['file_path']}:{routine['line_start']}-{routine['line_end']}\n"
                f"Type: {routine['routine_type']}\n"
                f"Calls: {', '.join(routine['calls']) if routine['calls'] else 'None'}\n\n"
                f"```fortran\n{content}\n```"
            ),
        }],
    )

    text = message.content[0].text
    code_match = re.search(r"```python\n(.*?)```", text, re.DOTALL)
    code = code_match.group(1).strip() if code_match else ""
    explanation = re.sub(r"```python\n.*?```", "", text, flags=re.DOTALL).strip() if code_match else text
    result = {
        "subroutine_name": routine["subroutine_name"],
        "code": code,
        "explanation": explanation or "See code below.",
    }
    if routine.get("corrected_from"):
        result["corrected_from"] = routine["corrected_from"]
    _put_cached(name, "translate", result)
    return result


def get_use_cases(name: str) -> dict | None:
    """Generate use case scenarios and when to use this routine."""
    cached = _get_cached(name, "use-cases")
    if cached:
        return cached

    routine = lookup_routine(name, include_embedding=False)
    if not routine:
        return None

    content = _truncate_for_llm(routine["content"])
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=(
            "You are a Fortran and LAPACK expert. Describe when a developer would use this routine. "
            "Include: typical use cases, calling patterns, when to prefer over alternatives. "
            "Use markdown. Be concise. Keep under 250 words."
        ),
        messages=[{
            "role": "user",
            "content": (
                f"Subroutine: {routine['subroutine_name']}\n"
                f"File: {routine['file_path']}:{routine['line_start']}-{routine['line_end']}\n"
                f"Type: {routine['routine_type']}\n"
                f"Calls: {', '.join(routine['calls']) if routine['calls'] else 'None'}\n\n"
                f"```fortran\n{content}\n```"
            ),
        }],
    )

    result = {
        "subroutine_name": routine["subroutine_name"],
        "use_cases": message.content[0].text,
        "typical_callers": [],
    }
    if routine.get("corrected_from"):
        result["corrected_from"] = routine["corrected_from"]
    _put_cached(name, "use-cases", result)
    return result
