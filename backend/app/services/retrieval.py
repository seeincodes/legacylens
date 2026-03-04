import hashlib
import json
import logging
import re
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

from app.config import settings
from app.models.schemas import ChunkResult

try:
    import anthropic
except ImportError:
    anthropic = None

logger = logging.getLogger("legacylens.retrieval")

_openai_client = None
_anthropic_client = None
_anthropic_module_ref = None
_executor = ThreadPoolExecutor(max_workers=6)


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        import openai
        _openai_client = openai.OpenAI(api_key=settings.openai_api_key)
    return _openai_client


def _get_anthropic_client():
    global _anthropic_client, _anthropic_module_ref
    if _anthropic_client is None or _anthropic_module_ref is not anthropic:
        _anthropic_module_ref = anthropic
        if anthropic is not None:
            _anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        else:
            _anthropic_client = None
    return _anthropic_client


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


# ── Response cache (LRU, max 512 entries) ─────────────────

_RESPONSE_CACHE_MAX = 512
_response_cache: OrderedDict[str, list] = OrderedDict()


def _response_cache_key(query: str, top_k: int, routine_type: str | None,
                        precision_type: str | None, blas_level: str | None,
                        expand: bool, rerank: bool) -> str:
    raw = json.dumps([query, top_k, routine_type, precision_type, blas_level, expand, rerank])
    return hashlib.sha256(raw.encode()).hexdigest()


def _get_cached_response(key: str) -> list | None:
    if key in _response_cache:
        _response_cache.move_to_end(key)
        return _response_cache[key]
    return None


def _put_cached_response(key: str, results: list) -> None:
    _response_cache[key] = results
    _response_cache.move_to_end(key)
    while len(_response_cache) > _RESPONSE_CACHE_MAX:
        _response_cache.popitem(last=False)


# ── Query type detection ──────────────────────────────────

_ROUTINE_QUERY_RE = re.compile(
    r"^(?:what\s+(?:is|does)|explain|describe|show\s+me)\s+(\w{3,8})\b",
    re.IGNORECASE,
)


def _is_routine_lookup(query: str) -> bool:
    """Detect if query is asking about a specific routine by name."""
    from app.services.routine_index import _looks_like_routine_name
    words = query.strip().split()
    if len(words) == 1 and _looks_like_routine_name(words[0]):
        return True
    m = _ROUTINE_QUERY_RE.match(query.strip())
    if m and _looks_like_routine_name(m.group(1)):
        return True
    return False


# ── Core functions ───────────────────────────────────────

def reciprocal_rank_fusion(
    vector_results: list[dict],
    keyword_results: list[dict],
    k: int = 60,
    vector_weight: float = 1.0,
    keyword_weight: float = 1.0,
) -> list[dict]:
    scores: dict[int, float] = {}
    id_to_data: dict[int, dict] = {}

    for rank, r in enumerate(vector_results):
        rid = r["id"]
        scores[rid] = scores.get(rid, 0) + vector_weight / (k + rank + 1)
        id_to_data[rid] = r

    for rank, r in enumerate(keyword_results):
        rid = r["id"]
        scores[rid] = scores.get(rid, 0) + keyword_weight / (k + rank + 1)
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

    client = _get_openai_client()
    response = client.embeddings.create(model="text-embedding-3-small", input=query)
    embedding = response.data[0].embedding
    _put_cached_embedding(query, embedding)
    return embedding


def expand_query(query: str) -> list[str]:
    if anthropic is None:
        return [query]

    try:
        client = _get_anthropic_client()
        if client is None:
            return [query]
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
    blas_level: str | None = None,
) -> list[dict]:
    from app.db import get_connection

    with get_connection() as conn:
        cur = conn.cursor()

        conditions = []
        params: list[str] = []
        if routine_type:
            conditions.append("routine_type = %s")
            params.append(routine_type)
        if precision_type:
            conditions.append("precision_type = %s")
            params.append(precision_type)
        if blas_level:
            conditions.append("blas_level = %s")
            params.append(blas_level)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""SELECT id, file_path, line_start, line_end, subroutine_name,
                         routine_type, blas_level, content, metadata, 1 - (embedding <=> %s::vector) AS score
                  FROM code_chunks {where}
                  ORDER BY embedding <=> %s::vector LIMIT %s"""
        cur.execute(sql, [embedding, *params, embedding, top_k])

        rows = cur.fetchall()
        cur.close()

    return [
        {"id": r[0], "file_path": r[1], "line_start": r[2], "line_end": r[3],
         "subroutine_name": r[4], "routine_type": r[5], "blas_level": r[6],
         "content": r[7], "metadata": r[8], "score": float(r[9])}
        for r in rows
    ]


def keyword_search(
    query: str,
    top_k: int = 10,
    routine_type: str | None = None,
    precision_type: str | None = None,
    blas_level: str | None = None,
) -> list[dict]:
    from app.db import get_connection

    with get_connection() as conn:
        cur = conn.cursor()

        conditions = [
            "(fts @@ plainto_tsquery('english', %s) OR UPPER(subroutine_name) = UPPER(%s))"
        ]
        params: list = [query, query]
        if routine_type:
            conditions.append("routine_type = %s")
            params.append(routine_type)
        if precision_type:
            conditions.append("precision_type = %s")
            params.append(precision_type)
        if blas_level:
            conditions.append("blas_level = %s")
            params.append(blas_level)

        where = " AND ".join(conditions)
        sql = f"""SELECT id, file_path, line_start, line_end, subroutine_name,
                         routine_type, blas_level, content, metadata,
                         CASE WHEN UPPER(subroutine_name) = UPPER(%s) THEN 10.0
                              ELSE ts_rank(fts, plainto_tsquery('english', %s))
                         END AS score
                  FROM code_chunks WHERE {where}
                  ORDER BY score DESC LIMIT %s"""
        cur.execute(sql, [query, query, *params, top_k])

        rows = cur.fetchall()
        cur.close()

    return [
        {"id": r[0], "file_path": r[1], "line_start": r[2], "line_end": r[3],
         "subroutine_name": r[4], "routine_type": r[5], "blas_level": r[6],
         "content": r[7], "metadata": r[8], "score": float(r[9])}
        for r in rows
    ]


def _fetch_routines_by_names(names: list[str]) -> list[dict]:
    """Batch-fetch routines by name using a single IN query."""
    if not names:
        return []
    from app.db import get_connection
    upper_names = [n.upper() for n in names]
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT DISTINCT ON (UPPER(subroutine_name))
                      id, file_path, line_start, line_end, subroutine_name,
                      routine_type, blas_level, content, metadata
               FROM code_chunks
               WHERE UPPER(subroutine_name) = ANY(%s)
               ORDER BY UPPER(subroutine_name), id""",
            (upper_names,),
        )
        rows = cur.fetchall()
        cur.close()
    return [
        {"id": r[0], "file_path": r[1], "line_start": r[2], "line_end": r[3],
         "subroutine_name": r[4], "routine_type": r[5], "blas_level": r[6],
         "content": r[7], "metadata": r[8]}
        for r in rows
    ]


def concept_boost(query: str, existing_results: list[dict]) -> list[dict]:
    """Inject matching D-prefix routines from the concept map into results.
    Falls back to fuzzy routine name match when query looks like a single routine name."""
    from app.services.concept_map import find_stems_for_query
    from app.services.routine_index import fuzzy_match_routine, _looks_like_routine_name

    matching_stems = find_stems_for_query(query)
    fuzzy_names_to_inject: list[str] = []
    if not matching_stems and _looks_like_routine_name(query):
        corrected = fuzzy_match_routine(query)
        if corrected:
            if corrected[0].upper() in "SDCZ" and len(corrected) > 1:
                matching_stems = [corrected[1:]]
            else:
                fuzzy_names_to_inject = [corrected]
    if not matching_stems and not fuzzy_names_to_inject:
        return existing_results

    existing_ids = {r["id"] for r in existing_results}
    boosted = list(existing_results)

    # Batch-fetch all needed names in one query
    all_names = list(fuzzy_names_to_inject) + [f"D{stem}" for stem in matching_stems]
    fetched = _fetch_routines_by_names(all_names)
    fetched_by_name = {(r["subroutine_name"] or "").upper(): r for r in fetched}

    for name in fuzzy_names_to_inject:
        row = fetched_by_name.get(name.upper())
        if row and row["id"] not in existing_ids:
            boosted.append({**row, "rrf_score": 999.0})
            existing_ids.add(row["id"])

    for stem in matching_stems:
        d_name = f"D{stem}".upper()
        row = fetched_by_name.get(d_name)
        if row and row["id"] not in existing_ids:
            boosted.append({**row, "rrf_score": 999.0})
            existing_ids.add(row["id"])
        elif row and row["id"] in existing_ids:
            for r in boosted:
                if r["id"] == row["id"]:
                    r["rrf_score"] = r.get("rrf_score", 0) + 999.0
                    break

    # Expand call graph: for concept-boosted routines, inject routines they call
    boosted_names = set()
    for r in boosted:
        if r.get("rrf_score", 0) >= 999.0:
            meta = r.get("metadata") or {}
            calls = meta.get("calls", []) if isinstance(meta, dict) else []
            boosted_names.update(calls)

    if boosted_names:
        existing_names = {(r.get("subroutine_name") or "").upper() for r in boosted}
        names_to_fetch = [n for n in boosted_names if n.upper() not in existing_names][:5]
        if names_to_fetch:
            call_rows = _fetch_routines_by_names(names_to_fetch)
            for row in call_rows:
                if row["id"] not in existing_ids:
                    boosted.append({**row, "rrf_score": 500.0})
                    existing_ids.add(row["id"])

    return boosted


def llm_rerank(query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
    """Use Claude Haiku to re-rank retrieval candidates by relevance.

    Falls back to original ranking on any failure.
    """
    if not candidates or anthropic is None:
        return candidates[:top_k]

    client = _get_anthropic_client()
    if client is None:
        return candidates[:top_k]

    limit = min(len(candidates), 15)
    descriptions = []
    from app.services.ingestion import extract_description
    from app.services.concept_map import get_concepts_for_stem, get_stem_from_routine_name
    for i, r in enumerate(candidates[:limit]):
        name = r.get("subroutine_name", "unknown")
        rtype = r.get("routine_type", "")
        content = r.get("content", "")
        desc = extract_description(content)
        if not desc:
            for line in content.split("\n"):
                stripped = line.strip()
                if stripped.startswith("*") or stripped.startswith("!"):
                    cleaned = stripped.lstrip("*! ").strip()
                    if len(cleaned) > 10:
                        desc = cleaned[:120]
                        break
        stem = get_stem_from_routine_name(name)
        concepts = get_concepts_for_stem(stem)
        concept_str = f" [{', '.join(concepts[:3])}]" if concepts else ""
        descriptions.append(f"{i}: {name} ({rtype}) - {desc[:150]}{concept_str}")

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=80,
            messages=[{
                "role": "user",
                "content": (
                    f"Query: \"{query}\"\n\n"
                    f"Rank by relevance to the query. Prefer primary driver/computational "
                    f"routines over auxiliary helpers. For routine lookups, the exact routine "
                    f"must be first. For concept queries, include the most representative "
                    f"routines for that algorithm. Return ONLY indices, comma-separated.\n\n"
                    + "\n".join(descriptions)
                ),
            }],
        )

        text = response.content[0].text.strip()
        indices = []
        for token in text.replace(" ", "").split(","):
            token = token.strip()
            if token.isdigit():
                idx = int(token)
                if 0 <= idx < limit and idx not in indices:
                    indices.append(idx)

        if not indices:
            return candidates[:top_k]

        reranked = [candidates[i] for i in indices]

        # Pin exact subroutine name matches at the front to prevent
        # the re-ranker from accidentally dropping direct lookups.
        query_upper = query.upper()
        pinned = []
        remaining = []
        for r in reranked:
            name = (r.get("subroutine_name") or "").upper()
            if name and name in query_upper:
                pinned.append(r)
            else:
                remaining.append(r)
        reranked = pinned + remaining

        seen_ids = {r["id"] for r in reranked}
        for r in candidates:
            if len(reranked) >= top_k:
                break
            if r["id"] not in seen_ids:
                reranked.append(r)
                seen_ids.add(r["id"])

        return reranked[:top_k]

    except Exception as exc:
        logger.warning("LLM rerank failed, using original ranking: %s", exc)
        return candidates[:top_k]


def search(
    query: str,
    top_k: int = 5,
    routine_type: str | None = None,
    precision_type: str | None = None,
    blas_level: str | None = None,
    expand: bool = False,
    rerank: bool = True,
) -> list[ChunkResult]:
    t0 = time.perf_counter()

    # ── Response cache check ──
    cache_key = _response_cache_key(query, top_k, routine_type, precision_type,
                                     blas_level, expand, rerank)
    cached = _get_cached_response(cache_key)
    if cached is not None:
        logger.info("search cache hit query=%r total_ms=%.1f", query[:80],
                     (time.perf_counter() - t0) * 1000)
        return cached

    # ── Query type detection for RRF weighting ──
    is_routine = _is_routine_lookup(query)

    queries = expand_query(query) if expand else [query]
    t_expand = time.perf_counter()

    pool_size = 15 if rerank else 10

    # ── Parallel: embed all variants + keyword search concurrently ──
    embed_futures = [_executor.submit(embed_query, q) for q in queries]
    kw_future = _executor.submit(
        keyword_search, query, pool_size, routine_type, precision_type, blas_level,
    )

    embeddings = [f.result() for f in embed_futures]

    # ── Parallel: all vector searches concurrently ──
    vec_futures = [
        _executor.submit(vector_search, emb, pool_size, routine_type, precision_type, blas_level)
        for emb in embeddings
    ]

    vector_results = []
    for f in vec_futures:
        vector_results.extend(f.result())
    t_vector = time.perf_counter()

    kw_results = kw_future.result()
    t_keyword = time.perf_counter()

    # ── Query-type-aware RRF weighting ──
    if is_routine:
        merged = reciprocal_rank_fusion(vector_results, kw_results,
                                         vector_weight=1.0, keyword_weight=1.5)
    else:
        merged = reciprocal_rank_fusion(vector_results, kw_results,
                                         vector_weight=1.2, keyword_weight=1.0)

    # Concept boost: inject matching routines from concept map
    merged = concept_boost(query, merged)

    # D-prefix boost and helper penalty — only for concept searches.
    # For routine lookups, the user asked for a specific routine; don't displace it.
    if not precision_type and not is_routine:
        for r in merged:
            name = (r.get("subroutine_name") or "")
            if not name:
                continue
            if name[0].upper() == "D":
                r["rrf_score"] = r["rrf_score"] * 2.0
            if name[-1].isdigit():
                r["rrf_score"] = r["rrf_score"] * 0.5

    merged.sort(key=lambda x: x.get("rrf_score", 0), reverse=True)
    merged = normalize_scores(merged)

    # LLM re-ranking
    if rerank:
        t_rerank_start = time.perf_counter()
        merged = llm_rerank(query, merged, top_k=top_k)
        t_rerank = time.perf_counter()
        logger.info("rerank_ms=%.0f", (t_rerank - t_rerank_start) * 1000)

    logger.info(
        "search query=%r is_routine=%s expand_ms=%.0f vector_ms=%.0f keyword_ms=%.0f "
        "total_ms=%.0f vector_hits=%d keyword_hits=%d merged=%d rerank=%s",
        query[:80],
        is_routine,
        (t_expand - t0) * 1000,
        (t_vector - t_expand) * 1000,
        (t_keyword - t_vector) * 1000,
        (time.perf_counter() - t0) * 1000,
        len(vector_results),
        len(kw_results),
        len(merged),
        rerank,
    )

    results = []
    for r in merged[:top_k]:
        meta = r.get("metadata") or {}
        calls = meta.get("calls") if isinstance(meta, dict) else None
        results.append(
            ChunkResult(
                file_path=r["file_path"], line_start=r["line_start"], line_end=r["line_end"],
                subroutine_name=r.get("subroutine_name"), routine_type=r.get("routine_type"),
                blas_level=r.get("blas_level"),
                content=r["content"], relevance_score=round(r.get("rrf_score", 0), 4),
                relevance_label=r.get("relevance_label", "Medium"),
                calls=calls,
            )
        )

    _put_cached_response(cache_key, results)
    return results
