"""Full library call graph endpoint."""

from fastapi import APIRouter, Query

from app.db import get_connection

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("")
async def get_graph(
    routine_type: str | None = Query(None, description="Filter by routine_type"),
    limit: int = Query(2000, ge=1, le=5000, description="Max nodes to return"),
):
    """Return the full call graph (or filtered subset) for visualization.

    Nodes: routines with id, routine_type, file_path.
    Links: caller -> callee edges from metadata.calls.
    """
    with get_connection() as conn:
        cur = conn.cursor()

        # Build node set from routines that appear as callers or callees
        # Get all (caller, callee) pairs first
        cur.execute(
            """
            SELECT subroutine_name AS caller,
                   jsonb_array_elements_text(metadata->'calls') AS callee
            FROM code_chunks
            WHERE subroutine_name IS NOT NULL
              AND metadata->'calls' IS NOT NULL
              AND jsonb_typeof(metadata->'calls') = 'array'
              AND jsonb_array_length(metadata->'calls') > 0
            """
        )
        pairs = cur.fetchall()

        # Apply routine_type filter if specified (filter by caller only)
        if routine_type:
            cur.execute(
                """
                SELECT subroutine_name FROM code_chunks
                WHERE subroutine_name IS NOT NULL AND routine_type = %s
                """,
                (routine_type,),
            )
            allowed = {r[0].upper() for r in cur.fetchall()}
            pairs = [(c, cal) for c, cal in pairs if c and cal and c.upper() in allowed]

        # Collect unique node names
        node_names = set()
        for caller, callee in pairs:
            if caller and callee:
                node_names.add(caller)
                node_names.add(callee)

        # Cap nodes - keep most connected (by degree) if over limit
        if len(node_names) > limit:
            in_degree = {}
            out_degree = {}
            for caller, callee in pairs:
                if caller and callee:
                    out_degree[caller] = out_degree.get(caller, 0) + 1
                    in_degree[callee] = in_degree.get(callee, 0) + 1
            scores = {n: in_degree.get(n, 0) + out_degree.get(n, 0) for n in node_names}
            node_names = set(sorted(node_names, key=lambda n: -scores.get(n, 0))[:limit])

        # Filter links to only include nodes we're keeping
        links = [
            {"source": c, "target": cal}
            for c, cal in pairs
            if c and cal and c in node_names and cal in node_names
        ]

        # Fetch node metadata for kept nodes
        if node_names:
            placeholders = ",".join(["%s"] * len(node_names))
            cur.execute(
                f"""
                SELECT DISTINCT ON (subroutine_name) subroutine_name, routine_type, file_path
                FROM code_chunks
                WHERE subroutine_name IN ({placeholders})
                ORDER BY subroutine_name, line_start
                """,
                tuple(node_names),
            )
            rows = cur.fetchall()
        else:
            rows = []

        cur.close()

    node_by_name = {r[0]: {"routine_type": r[1], "file_path": r[2]} for r in rows}
    nodes = [
        {
            "id": name,
            "routine_type": node_by_name.get(name, {}).get("routine_type"),
            "file_path": node_by_name.get(name, {}).get("file_path"),
        }
        for name in node_names
    ]

    return {"nodes": nodes, "links": links}
