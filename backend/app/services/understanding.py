import json

import anthropic
import openai
import psycopg2
from pgvector.psycopg2 import register_vector

from app.config import settings


def _get_conn():
    conn = psycopg2.connect(settings.database_url)
    register_vector(conn)
    return conn


def lookup_routine(name: str) -> dict | None:
    """Find a routine by name (case-insensitive). Returns dict with all fields or None."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT id, file_path, line_start, line_end, subroutine_name,
                  routine_type, content, metadata, embedding
           FROM code_chunks
           WHERE subroutine_name ILIKE %s
           LIMIT 1""",
        (name,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return None

    meta = row[7] if isinstance(row[7], dict) else (json.loads(row[7]) if row[7] else {})
    return {
        "id": row[0],
        "file_path": row[1],
        "line_start": row[2],
        "line_end": row[3],
        "subroutine_name": row[4],
        "routine_type": row[5],
        "content": row[6],
        "metadata": meta,
        "calls": meta.get("calls", []),
        "embedding": row[8],
    }


def _generate_explanation(name: str, system_prompt: str) -> dict | None:
    """Look up a routine and generate an explanation via Claude."""
    routine = lookup_routine(name)
    if not routine:
        return None

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=system_prompt,
        messages=[{
            "role": "user",
            "content": (
                f"Subroutine: {routine['subroutine_name']}\n"
                f"File: {routine['file_path']}:{routine['line_start']}-{routine['line_end']}\n"
                f"Type: {routine['routine_type']}\n\n"
                f"```fortran\n{routine['content']}\n```"
            ),
        }],
    )

    return {
        "subroutine_name": routine["subroutine_name"],
        "routine_type": routine["routine_type"],
        "file_path": routine["file_path"],
        "line_start": routine["line_start"],
        "line_end": routine["line_end"],
        "explanation": message.content[0].text,
        "calls": routine["calls"],
    }


def explain_routine(name: str) -> dict | None:
    """Look up a routine and generate a plain-English explanation via Claude."""
    return _generate_explanation(
        name,
        (
            "You are a Fortran and LAPACK expert. Explain the following subroutine in plain English. "
            "Cover: what it does, its parameters, the algorithm used, and when you'd use it. Be concise."
        ),
    )


def explain_routine_eli5(name: str) -> dict | None:
    """Look up a routine and explain it in simple ELI5 language with emoji visuals."""
    return _generate_explanation(
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
    )


def build_dependency_graph(name: str, max_depth: int = 3) -> dict | None:
    """BFS traversal of call chains using metadata.calls."""
    root = lookup_routine(name)
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

    return {
        "root": root["subroutine_name"],
        "nodes": nodes,
        "max_depth": max_depth,
    }


def find_similar_routines(name: str, top_k: int = 5) -> dict | None:
    """Find routines with similar embeddings, excluding the source routine."""
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

    return {"subroutine_name": routine["subroutine_name"], "similar": similar}


def generate_documentation(name: str) -> dict | None:
    """Generate structured documentation for a routine via Claude."""
    routine = lookup_routine(name)
    if not routine:
        return None

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        system=(
            "You are a Fortran and LAPACK documentation expert. Generate structured documentation "
            "for the following subroutine. Include these sections:\n"
            "1. PURPOSE - What the routine does\n"
            "2. PARAMETERS - Each parameter with type, intent, and description\n"
            "3. ALGORITHM - Step-by-step explanation of the algorithm\n"
            "4. RETURN VALUES - What INFO values mean\n"
            "5. DEPENDENCIES - Called routines and their roles\n"
            "Format in clean markdown."
        ),
        messages=[{
            "role": "user",
            "content": (
                f"Subroutine: {routine['subroutine_name']}\n"
                f"File: {routine['file_path']}:{routine['line_start']}-{routine['line_end']}\n"
                f"Type: {routine['routine_type']}\n"
                f"Calls: {', '.join(routine['calls']) if routine['calls'] else 'None'}\n\n"
                f"```fortran\n{routine['content']}\n```"
            ),
        }],
    )

    return {
        "subroutine_name": routine["subroutine_name"],
        "documentation": message.content[0].text,
    }


def find_entry_points(top_k: int = 10) -> dict:
    """Find driver routines (main entry points) and summarize them."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT file_path, line_start, line_end, subroutine_name,
                  routine_type, content
           FROM code_chunks
           WHERE routine_type = 'driver'
           ORDER BY subroutine_name
           LIMIT %s""",
        (top_k,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        return {"analysis_type": "entry_points", "analysis": "No driver routines found.", "chunks": []}

    chunks = []
    summaries = []
    for r in rows:
        preview = r[5][:300] + "..." if len(r[5]) > 300 else r[5]
        chunks.append({
            "file_path": r[0],
            "subroutine_name": r[3],
            "content_preview": preview,
        })
        summaries.append(f"- {r[3]} ({r[0]}:{r[1]}-{r[2]})")

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    context = "\n".join(summaries)
    code_context = "\n\n".join(
        f"### {r[3]} ({r[0]})\n```fortran\n{r[5][:1000]}\n```"
        for r in rows
    )
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=(
            "You are a Fortran and LAPACK expert. The user wants to know the main entry points "
            "(driver routines) of the LAPACK library. Summarize what each driver routine does, "
            "what problem it solves, and when you'd use it. Be concise but informative. "
            "Group them by category if possible (e.g., linear solvers, eigenvalue, SVD)."
        ),
        messages=[{"role": "user", "content": f"Driver routines found:\n{context}\n\nCode:\n{code_context}"}],
    )

    return {
        "analysis_type": "entry_points",
        "analysis": message.content[0].text,
        "chunks": chunks,
    }


def find_data_usage(variable_name: str, top_k: int = 10) -> dict:
    """Find routines that reference a given variable/array name."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT file_path, line_start, line_end, subroutine_name,
                  routine_type, content
           FROM code_chunks
           WHERE content ILIKE %s
           ORDER BY subroutine_name
           LIMIT %s""",
        (f"%{variable_name}%", top_k),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        return {
            "analysis_type": "data_usage",
            "analysis": f"No routines found referencing '{variable_name}'.",
            "chunks": [],
        }

    chunks = []
    code_context_parts = []
    for r in rows:
        preview = r[5][:300] + "..." if len(r[5]) > 300 else r[5]
        chunks.append({
            "file_path": r[0],
            "subroutine_name": r[3],
            "content_preview": preview,
        })
        code_context_parts.append(f"### {r[3]} ({r[0]})\n```fortran\n{r[5][:1000]}\n```")

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=(
            f"You are a Fortran and LAPACK expert. The user wants to know which routines "
            f"use or modify the variable/parameter '{variable_name}'. For each routine, explain: "
            f"1) Whether it reads or modifies '{variable_name}' "
            f"2) What role '{variable_name}' plays in that routine "
            f"3) Any important constraints or conventions. Be concise."
        ),
        messages=[{"role": "user", "content": f"Routines referencing '{variable_name}':\n\n" + "\n\n".join(code_context_parts)}],
    )

    return {
        "analysis_type": "data_usage",
        "analysis": message.content[0].text,
        "chunks": chunks,
    }


def find_io_operations(top_k: int = 10) -> dict:
    """Find routines containing file I/O operations (WRITE, READ, OPEN, CLOSE, PRINT)."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT file_path, line_start, line_end, subroutine_name,
                  routine_type, content
           FROM code_chunks
           WHERE content ~* '\\m(WRITE|READ|OPEN|CLOSE|PRINT)\\s*\\('
           ORDER BY subroutine_name
           LIMIT %s""",
        (top_k,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        return {"analysis_type": "io_operations", "analysis": "No I/O operations found.", "chunks": []}

    chunks = []
    code_context_parts = []
    for r in rows:
        preview = r[5][:300] + "..." if len(r[5]) > 300 else r[5]
        chunks.append({
            "file_path": r[0],
            "subroutine_name": r[3],
            "content_preview": preview,
        })
        code_context_parts.append(f"### {r[3]} ({r[0]})\n```fortran\n{r[5][:1000]}\n```")

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=(
            "You are a Fortran and LAPACK expert. The user wants to find all file I/O operations "
            "in the codebase. For each routine, identify: "
            "1) What I/O statements it uses (WRITE, READ, OPEN, CLOSE, PRINT) "
            "2) What it reads from or writes to (stdout, files, etc.) "
            "3) The purpose of the I/O operation. "
            "Categorize them (error reporting, debug output, data I/O, etc.). Be concise."
        ),
        messages=[{"role": "user", "content": "Routines with I/O operations:\n\n" + "\n\n".join(code_context_parts)}],
    )

    return {
        "analysis_type": "io_operations",
        "analysis": message.content[0].text,
        "chunks": chunks,
    }


def find_error_patterns(top_k: int = 10) -> dict:
    """Find error handling patterns (XERBLA calls, INFO checks)."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT file_path, line_start, line_end, subroutine_name,
                  routine_type, content
           FROM code_chunks
           WHERE content ILIKE '%XERBLA%' OR content ILIKE '%INFO.NE.0%' OR content ILIKE '%INFO.LT.0%'
           ORDER BY subroutine_name
           LIMIT %s""",
        (top_k,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        return {"analysis_type": "error_patterns", "analysis": "No error handling patterns found.", "chunks": []}

    chunks = []
    code_context_parts = []
    for r in rows:
        preview = r[5][:300] + "..." if len(r[5]) > 300 else r[5]
        chunks.append({
            "file_path": r[0],
            "subroutine_name": r[3],
            "content_preview": preview,
        })
        code_context_parts.append(f"### {r[3]} ({r[0]})\n```fortran\n{r[5][:1000]}\n```")

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=(
            "You are a Fortran and LAPACK expert. The user wants to understand error handling patterns "
            "in the codebase. Analyze the routines and explain: "
            "1) How XERBLA is used for input validation "
            "2) How the INFO parameter reports errors "
            "3) Common error handling patterns and conventions "
            "4) Categories of errors (invalid input, computational failure, etc.). Be concise."
        ),
        messages=[{"role": "user", "content": "Routines with error handling:\n\n" + "\n\n".join(code_context_parts)}],
    )

    return {
        "analysis_type": "error_patterns",
        "analysis": message.content[0].text,
        "chunks": chunks,
    }
