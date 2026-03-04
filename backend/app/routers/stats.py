"""Codebase statistics endpoint."""

import logging

from fastapi import APIRouter

from app.db import get_connection

logger = logging.getLogger("legacylens.stats")

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
async def get_stats():
    """Return aggregated codebase statistics."""
    with get_connection() as conn:
        cur = conn.cursor()

        # Totals
        cur.execute(
            """
            SELECT
                COUNT(*) as total_routines,
                COUNT(DISTINCT file_path) as total_files,
                COALESCE(SUM(line_end - line_start + 1), 0)::bigint as total_loc
            FROM code_chunks
            WHERE subroutine_name IS NOT NULL
            """
        )
        row = cur.fetchone()
        total_routines = row[0] or 0
        total_files = row[1] or 0
        total_loc = row[2] or 0

        # By routine_type
        cur.execute(
            """
            SELECT routine_type, COUNT(*) as cnt
            FROM code_chunks
            WHERE subroutine_name IS NOT NULL AND routine_type IS NOT NULL
            GROUP BY routine_type
            ORDER BY cnt DESC
            """
        )
        by_routine_type = [{"routine_type": r[0], "count": r[1]} for r in cur.fetchall()]

        # By precision_type
        cur.execute(
            """
            SELECT precision_type, COUNT(*) as cnt
            FROM code_chunks
            WHERE subroutine_name IS NOT NULL AND precision_type IS NOT NULL
            GROUP BY precision_type
            ORDER BY cnt DESC
            """
        )
        by_precision = [{"precision_type": r[0], "count": r[1]} for r in cur.fetchall()]

        # Top 10 largest routines (by line count)
        cur.execute(
            """
            SELECT subroutine_name, file_path, line_end - line_start + 1 as lines
            FROM code_chunks
            WHERE subroutine_name IS NOT NULL
            ORDER BY (line_end - line_start + 1) DESC
            LIMIT 10
            """
        )
        largest_routines = [
            {"subroutine_name": r[0], "file_path": r[1], "lines": r[2]}
            for r in cur.fetchall()
        ]

        # Top 10 most-called routines (in-degree from metadata.calls)
        cur.execute(
            """
            WITH callees AS (
                SELECT jsonb_array_elements_text(metadata->'calls') AS callee
                FROM code_chunks
                WHERE metadata->'calls' IS NOT NULL
                  AND jsonb_typeof(metadata->'calls') = 'array'
                  AND jsonb_array_length(metadata->'calls') > 0
            )
            SELECT callee, COUNT(*) AS call_count
            FROM callees
            WHERE callee IS NOT NULL AND callee != ''
            GROUP BY callee
            ORDER BY call_count DESC
            LIMIT 10
            """
        )
        most_called = [{"subroutine_name": r[0], "call_count": r[1]} for r in cur.fetchall()]

        cur.close()

    return {
        "total_routines": total_routines,
        "total_files": total_files,
        "total_loc": total_loc,
        "by_routine_type": by_routine_type,
        "by_precision": by_precision,
        "largest_routines": largest_routines,
        "most_called": most_called,
    }
