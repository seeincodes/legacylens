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

_openai_client = None
_anthropic_client = None
_anthropic_module_ref = None


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
                matching_stems = [corrected[1:]]  # stem without precision prefix
            else:
                fuzzy_names_to_inject = [corrected]
    if not matching_stems and not fuzzy_names_to_inject:
        return existing_results

    from app.db import get_connection

    existing_ids = {r["id"] for r in existing_results}
    boosted = list(existing_results)

    with get_connection() as conn:
        cur = conn.cursor()
        for name in fuzzy_names_to_inject:
            cur.execute(
                """SELECT id, file_path, line_start, line_end, subroutine_name,
                          routine_type, blas_level, content, metadata
                   FROM code_chunks
                   WHERE UPPER(subroutine_name) = UPPER(%s)
                   LIMIT 1""",
                (name,),
            )
            row = cur.fetchone()
            if row and row[0] not in existing_ids:
                boosted.append({
                    "id": row[0], "file_path": row[1], "line_start": row[2],
                    "line_end": row[3], "subroutine_name": row[4],
                    "routine_type": row[5], "blas_level": row[6],
                    "content": row[7], "metadata": row[8], "rrf_score": 999.0,
                })
                existing_ids.add(row[0])
        for stem in matching_stems:
            d_name = f"D{stem}"
            cur.execute(
                """SELECT id, file_path, line_start, line_end, subroutine_name,
                          routine_type, blas_level, content, metadata
                   FROM code_chunks
                   WHERE UPPER(subroutine_name) = UPPER(%s)
                   LIMIT 1""",
                (d_name,),
            )
            row = cur.fetchone()
            if row and row[0] not in existing_ids:
                boosted.append({
                    "id": row[0], "file_path": row[1], "line_start": row[2],
                    "line_end": row[3], "subroutine_name": row[4],
                    "routine_type": row[5], "blas_level": row[6],
                    "content": row[7], "metadata": row[8], "rrf_score": 999.0,
                })
                existing_ids.add(row[0])
            elif row and row[0] in existing_ids:
                for r in boosted:
                    if r["id"] == row[0]:
                        r["rrf_score"] = r.get("rrf_score", 0) + 999.0
                        break
        cur.close()

    # Expand call graph: for concept-boosted routines, inject routines they call
    boosted_names = set()
    for r in boosted:
        if r.get("rrf_score", 0) >= 999.0:
            meta = r.get("metadata") or {}
            calls = meta.get("calls", []) if isinstance(meta, dict) else []
            boosted_names.update(calls)

    if boosted_names:
        existing_names = {(r.get("subroutine_name") or "").upper() for r in boosted}
        names_to_fetch = [n for n in boosted_names if n.upper() not in existing_names]
        if names_to_fetch:
            with get_connection() as conn:
                cur = conn.cursor()
                for name in names_to_fetch[:5]:
                    cur.execute(
                        """SELECT id, file_path, line_start, line_end, subroutine_name,
                                  routine_type, blas_level, content, metadata
                           FROM code_chunks
                           WHERE UPPER(subroutine_name) = UPPER(%s)
                           LIMIT 1""",
                        (name,),
                    )
                    row = cur.fetchone()
                    if row and row[0] not in existing_ids:
                        boosted.append({
                            "id": row[0], "file_path": row[1], "line_start": row[2],
                            "line_end": row[3], "subroutine_name": row[4],
                            "routine_type": row[5], "blas_level": row[6],
                            "content": row[7], "metadata": row[8], "rrf_score": 500.0,
                        })
                        existing_ids.add(row[0])
                cur.close()

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
    for i, r in enumerate(candidates[:limit]):
        name = r.get("subroutine_name", "unknown")
        rtype = r.get("routine_type", "")
        content = r.get("content", "")
        # Use extract_description for a rich description
        from app.services.ingestion import extract_description
        desc = extract_description(content)
        if not desc:
            # Fallback: first comment line
            for line in content.split("\n"):
                stripped = line.strip()
                if stripped.startswith("*") or stripped.startswith("!"):
                    cleaned = stripped.lstrip("*! ").strip()
                    if len(cleaned) > 10:
                        desc = cleaned[:120]
                        break
        # Add concept terms if available
        from app.services.concept_map import get_concepts_for_stem, get_stem_from_routine_name
        stem = get_stem_from_routine_name(name)
        concepts = get_concepts_for_stem(stem)
        concept_str = f" [{', '.join(concepts[:3])}]" if concepts else ""
        descriptions.append(f"{i}: {name} ({rtype}) - {desc[:150]}{concept_str}")

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            messages=[{
                "role": "user",
                "content": (
                    f"Given the LAPACK/linear algebra query: \"{query}\"\n\n"
                    f"Rank these routines by relevance. Include the primary routine "
                    f"AND closely related routines (same algorithm family, called by "
                    f"or calling the main routine). Put most relevant first. "
                    f"Return ONLY the indices as comma-separated numbers.\n\n"
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
    queries = expand_query(query) if expand else [query]
    t_expand = time.perf_counter()

    pool_size = 15 if rerank else 10

    vector_results = []
    for query_variant in queries:
        query_embedding = embed_query(query_variant)
        vector_results.extend(
            vector_search(
                query_embedding,
                top_k=pool_size,
                routine_type=routine_type,
                precision_type=precision_type,
                blas_level=blas_level,
            )
        )
    t_vector = time.perf_counter()

    kw_results = keyword_search(
        query,
        top_k=pool_size,
        routine_type=routine_type,
        precision_type=precision_type,
        blas_level=blas_level,
    )
    t_keyword = time.perf_counter()

    merged = reciprocal_rank_fusion(vector_results, kw_results)

    # Concept boost: inject matching routines from concept map
    merged = concept_boost(query, merged)

    # When no precision filter is set, boost double-precision (D-prefix) results
    # and penalize level-2 helper routines (names ending in digits like POTRF2).
    if not precision_type:
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
        "search query=%r expand_ms=%.0f vector_ms=%.0f keyword_ms=%.0f total_ms=%.0f "
        "vector_hits=%d keyword_hits=%d merged=%d rerank=%s",
        query[:80],
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
    return results
