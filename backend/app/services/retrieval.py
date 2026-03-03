import hashlib
import logging
import time
from collections import OrderedDict

from app.config import settings
from app.models.schemas import ChunkResult

try:
    import anthropic
except ImportError:
    anthropic = None

logger = logging.getLogger("legacylens.retrieval")

# ── Embedding cache (LRU, max 256 entries) ──────────────

_EMBEDDING_CACHE_MAX = 256
_embedding_cache: OrderedDict[str, list[float]] = OrderedDict()


def _cache_key(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _get_cached_embedding(text: str) -> list[float] | None:
    key = _cache_key(text)
    if key in _embedding_cache:
        _embedding_cache.move_to_end(key)
        return _embedding_cache[key]
    return None


def _put_cached_embedding(text: str, embedding: list[float]) -> None:
    key = _cache_key(text)
    _embedding_cache[key] = embedding
    _embedding_cache.move_to_end(key)
    while len(_embedding_cache) > _EMBEDDING_CACHE_MAX:
        _embedding_cache.popitem(last=False)


# ── Core functions ───────────────────────────────────────

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


def normalize_scores(merged: list[dict]) -> list[dict]:
    if not merged:
        return []
    max_score = merged[0]["rrf_score"]
    if max_score == 0:
        return merged
    result = []
    for r in merged:
        normalized = r["rrf_score"] / max_score
        label = "High" if normalized > 0.7 else "Medium" if normalized > 0.4 else "Low"
        result.append({**r, "rrf_score": normalized, "relevance_label": label})
    return result


def embed_query(query: str) -> list[float]:
    cached = _get_cached_embedding(query)
    if cached is not None:
        logger.debug("embedding cache hit for query=%r", query[:50])
        return cached

    import openai

    client = openai.OpenAI(api_key=settings.openai_api_key)
    response = client.embeddings.create(model="text-embedding-3-small", input=query)
    embedding = response.data[0].embedding
    _put_cached_embedding(query, embedding)
    return embedding


def expand_query(query: str) -> list[str]:
    if anthropic is None:
        return [query]

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": (
                    "Rephrase this LAPACK/linear algebra search query into 2-3 "
                    "alternative search variants. Return ONLY the variants, one per "
                    "line, with no numbering or bullets.\n\n"
                    f"Query: {query}"
                ),
            }],
        )

        text_blocks = [
            block.text.strip()
            for block in response.content
            if getattr(block, "type", "") == "text" and getattr(block, "text", "").strip()
        ]
        variants = []
        for block in text_blocks:
            for line in block.splitlines():
                candidate = line.strip()
                if candidate:
                    variants.append(candidate)

        # Keep original first, add up to 3 unique variants.
        merged = [query]
        for variant in variants:
            if variant not in merged:
                merged.append(variant)
            if len(merged) >= 4:
                break
        return merged
    except Exception as exc:
        logger.warning("query expansion failed, using original query: %s", exc)
        return [query]


def vector_search(
    embedding: list[float],
    top_k: int = 10,
    routine_type: str | None = None,
    precision_type: str | None = None,
) -> list[dict]:
    import psycopg2
    from pgvector.psycopg2 import register_vector

    conn = psycopg2.connect(settings.database_url)
    register_vector(conn)
    cur = conn.cursor()

    conditions = []
    params: list[str] = []
    if routine_type:
        conditions.append("routine_type = %s")
        params.append(routine_type)
    if precision_type:
        conditions.append("precision_type = %s")
        params.append(precision_type)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"""SELECT id, file_path, line_start, line_end, subroutine_name,
                     routine_type, content, metadata, 1 - (embedding <=> %s::vector) AS score
              FROM code_chunks {where}
              ORDER BY embedding <=> %s::vector LIMIT %s"""
    cur.execute(sql, [embedding, *params, embedding, top_k])

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {"id": r[0], "file_path": r[1], "line_start": r[2], "line_end": r[3],
         "subroutine_name": r[4], "routine_type": r[5], "content": r[6],
         "metadata": r[7], "score": float(r[8])}
        for r in rows
    ]


def keyword_search(
    query: str,
    top_k: int = 10,
    routine_type: str | None = None,
    precision_type: str | None = None,
) -> list[dict]:
    import psycopg2

    conn = psycopg2.connect(settings.database_url)
    cur = conn.cursor()

    conditions = ["fts @@ plainto_tsquery('english', %s)"]
    params: list[str] = [query]
    if routine_type:
        conditions.append("routine_type = %s")
        params.append(routine_type)
    if precision_type:
        conditions.append("precision_type = %s")
        params.append(precision_type)

    where = " AND ".join(conditions)
    sql = f"""SELECT id, file_path, line_start, line_end, subroutine_name,
                     routine_type, content, metadata, ts_rank(fts, plainto_tsquery('english', %s)) AS score
              FROM code_chunks WHERE {where}
              ORDER BY score DESC LIMIT %s"""
    cur.execute(sql, [query, *params, top_k])

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {"id": r[0], "file_path": r[1], "line_start": r[2], "line_end": r[3],
         "subroutine_name": r[4], "routine_type": r[5], "content": r[6],
         "metadata": r[7], "score": float(r[8])}
        for r in rows
    ]


def search(
    query: str,
    top_k: int = 5,
    routine_type: str | None = None,
    precision_type: str | None = None,
    expand: bool = False,
) -> list[ChunkResult]:
    t0 = time.perf_counter()
    queries = expand_query(query) if expand else [query]
    t_expand = time.perf_counter()

    vector_results = []
    for query_variant in queries:
        query_embedding = embed_query(query_variant)
        vector_results.extend(
            vector_search(
                query_embedding,
                top_k=10,
                routine_type=routine_type,
                precision_type=precision_type,
            )
        )
    t_vector = time.perf_counter()

    kw_results = keyword_search(
        query,
        top_k=10,
        routine_type=routine_type,
        precision_type=precision_type,
    )
    t_keyword = time.perf_counter()

    merged = reciprocal_rank_fusion(vector_results, kw_results)
    merged = normalize_scores(merged)

    logger.info(
        "search query=%r expand_ms=%.0f vector_ms=%.0f keyword_ms=%.0f total_ms=%.0f "
        "vector_hits=%d keyword_hits=%d merged=%d",
        query[:80],
        (t_expand - t0) * 1000,
        (t_vector - t_expand) * 1000,
        (t_keyword - t_vector) * 1000,
        (t_keyword - t0) * 1000,
        len(vector_results),
        len(kw_results),
        len(merged),
    )

    results = []
    for r in merged[:top_k]:
        meta = r.get("metadata") or {}
        calls = meta.get("calls") if isinstance(meta, dict) else None
        results.append(
            ChunkResult(
                file_path=r["file_path"], line_start=r["line_start"], line_end=r["line_end"],
                subroutine_name=r.get("subroutine_name"), routine_type=r.get("routine_type"),
                content=r["content"], relevance_score=round(r["rrf_score"], 4),
                relevance_label=r.get("relevance_label", "Medium"),
                calls=calls,
            )
        )
    return results
