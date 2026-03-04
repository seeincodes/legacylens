"""Routine name index for fuzzy matching. Caches subroutine names from DB."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger("legacylens.routine_index")

_routine_names: list[str] | None = None


def get_all_routine_names() -> list[str]:
    """Fetch distinct subroutine names from code_chunks. Cached."""
    global _routine_names
    if _routine_names is not None:
        return _routine_names

    from app.db import get_connection

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT subroutine_name FROM code_chunks WHERE subroutine_name IS NOT NULL"
        )
        _routine_names = [row[0] for row in cur.fetchall() if row[0]]
        cur.close()

    logger.debug("loaded %d routine names", len(_routine_names))
    return _routine_names


def fuzzy_match_routine(query: str, threshold: float = 0.80) -> str | None:
    """Return best-matching routine name or None if below threshold."""
    if not query or not query.strip():
        return None

    from rapidfuzz import fuzz

    names = get_all_routine_names()
    if not names:
        return None

    q = query.strip().upper()
    best = max(names, key=lambda n: fuzz.ratio(q, n.upper()))
    score = fuzz.ratio(q, best.upper()) / 100.0
    return best if score >= threshold else None


def _looks_like_routine_name(text: str) -> bool:
    """Heuristic: is this a single LAPACK routine name (e.g. DGESV, XERBLA)?"""
    t = text.strip()
    if not t or len(t) < 3 or len(t) > 20:
        return False
    return t.replace("_", "").isalnum()
