import openai
import psycopg2
from pgvector.psycopg2 import register_vector

from app.config import settings
from app.models.schemas import ChunkResult


def reciprocal_rank_fusion(
    vector_results: list[dict],
    keyword_results: list[dict],
    k: int = 60,
) -> list[dict]:
    scores: dict[int, float] = {}
    id_to_data: dict[int, dict] = {}

    for rank, r in enumerate(vector_results):
        rid = r["id"]
        scores[rid] = scores.get(rid, 0) + 1.0 / (k + rank + 1)
        id_to_data[rid] = r

    for rank, r in enumerate(keyword_results):
        rid = r["id"]
        scores[rid] = scores.get(rid, 0) + 1.0 / (k + rank + 1)
        if rid not in id_to_data:
            id_to_data[rid] = r

    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    return [{**id_to_data[rid], "rrf_score": scores[rid]} for rid in sorted_ids]


def embed_query(query: str) -> list[float]:
    client = openai.OpenAI(api_key=settings.openai_api_key)
    response = client.embeddings.create(model="text-embedding-3-small", input=query)
    return response.data[0].embedding


def vector_search(embedding: list[float], top_k: int = 10, routine_type: str | None = None) -> list[dict]:
    conn = psycopg2.connect(settings.database_url)
    register_vector(conn)
    cur = conn.cursor()

    if routine_type:
        cur.execute(
            """SELECT id, file_path, line_start, line_end, subroutine_name,
                      routine_type, content, metadata, 1 - (embedding <=> %s::vector) AS score
               FROM code_chunks WHERE routine_type = %s
               ORDER BY embedding <=> %s::vector LIMIT %s""",
            (embedding, routine_type, embedding, top_k),
        )
    else:
        cur.execute(
            """SELECT id, file_path, line_start, line_end, subroutine_name,
                      routine_type, content, metadata, 1 - (embedding <=> %s::vector) AS score
               FROM code_chunks ORDER BY embedding <=> %s::vector LIMIT %s""",
            (embedding, embedding, top_k),
        )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {"id": r[0], "file_path": r[1], "line_start": r[2], "line_end": r[3],
         "subroutine_name": r[4], "routine_type": r[5], "content": r[6],
         "metadata": r[7], "score": float(r[8])}
        for r in rows
    ]


def keyword_search(query: str, top_k: int = 10) -> list[dict]:
    conn = psycopg2.connect(settings.database_url)
    cur = conn.cursor()

    cur.execute(
        """SELECT id, file_path, line_start, line_end, subroutine_name,
                  routine_type, content, metadata, ts_rank(fts, plainto_tsquery('english', %s)) AS score
           FROM code_chunks WHERE fts @@ plainto_tsquery('english', %s)
           ORDER BY score DESC LIMIT %s""",
        (query, query, top_k),
    )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {"id": r[0], "file_path": r[1], "line_start": r[2], "line_end": r[3],
         "subroutine_name": r[4], "routine_type": r[5], "content": r[6],
         "metadata": r[7], "score": float(r[8])}
        for r in rows
    ]


def search(query: str, top_k: int = 5, routine_type: str | None = None) -> list[ChunkResult]:
    query_embedding = embed_query(query)
    vector_results = vector_search(query_embedding, top_k=10, routine_type=routine_type)
    kw_results = keyword_search(query, top_k=10)
    merged = reciprocal_rank_fusion(vector_results, kw_results)

    results = []
    for r in merged[:top_k]:
        meta = r.get("metadata") or {}
        calls = meta.get("calls") if isinstance(meta, dict) else None
        results.append(
            ChunkResult(
                file_path=r["file_path"], line_start=r["line_start"], line_end=r["line_end"],
                subroutine_name=r.get("subroutine_name"), routine_type=r.get("routine_type"),
                content=r["content"], relevance_score=round(r["rrf_score"], 4),
                calls=calls,
            )
        )
    return results
