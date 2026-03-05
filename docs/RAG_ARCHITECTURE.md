# LegacyLens — RAG Architecture Document

## System Overview

LegacyLens is a Retrieval-Augmented Generation (RAG) system that makes the LAPACK Fortran codebase (~2,294 files, 977K LOC) searchable and explainable through natural language. Users type questions like "What does DGESV do?" and receive relevant code snippets with LLM-generated explanations citing specific file paths and line numbers.

```
                         ┌─────────────────┐
  User Query ──────────► │  Next.js Front  │
                         │  (Vercel)       │
                         └────────┬────────┘
                                  │ POST /api/query (SSE stream)
                                  │ GET  /api/graph, /api/stats
                                  ▼
                         ┌─────────────────┐
                         │  FastAPI Backend │
                         │  (Fly.io)       │
                         └──┬─────┬─────┬──┘
                            │     │     │
              ┌─────────────┘     │     └─────────────┐
              ▼                   ▼                   ▼
     ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
     │  OpenAI API  │   │   Supabase   │   │  Claude API  │
     │  (Embed)     │   │  PostgreSQL  │   │  (Generate,  │
     │              │   │  + pgvector  │   │   Rerank,    │
     └──────────────┘   └──────────────┘   │   Expand)    │
                                           └──────────────┘
```

## Ingestion Pipeline

**Goal:** Convert raw Fortran source into searchable, embedded chunks.

1. **File Discovery** — Recursively scans `SRC/` and `BLAS/SRC/` for `.f`, `.f90`, `.f95`, and `.f03` files.

2. **Syntax-Aware Chunking** — A regex-based Fortran parser extracts subroutine/function blocks by matching `SUBROUTINE`/`FUNCTION` definitions and their corresponding `END` statements. Each chunk includes its preceding comment block and records `line_start`/`line_end` for citation accuracy. HTML noise (`\htmlonly...\endhtmlonly` blocks and DOCUMENTATION banners) is stripped. Chunks that don't match a subroutine boundary fall back to the whole file.

3. **Metadata Extraction** — For each chunk:
   - **Precision type** inferred from filename prefix (`D`=double, `S`=single, `C`=complex, `Z`=double complex)
   - **Routine type** classified as `blas`, `driver`, or `computational` based on file path and call count heuristics
   - **BLAS level** parsed from "Reference BLAS level X routine" comment patterns (1=vector, 2=matrix-vector, 3=matrix-matrix)
   - **Call chain** extracted via regex matching of `CALL` statements
   - **Description** extracted from `\brief` or `\verbatim` comment sections (up to 200 chars)
   - **Concepts** linked from a concept map by routine stem

4. **Embedding** — Each chunk is prefixed with its metadata (file path, routine name, type, precision) and embedded with OpenAI `text-embedding-3-small` (1536 dimensions). Texts are truncated at 10K characters. Batched in groups of 100 with exponential backoff retry on rate limits.

5. **Storage** — Chunks, metadata (as JSONB), and embeddings are inserted into a PostgreSQL table with pgvector. A generated `tsvector` column enables full-text search.

**Indexes:**
- HNSW index on embeddings (cosine distance) for approximate nearest-neighbor search
- GIN index on the `fts` tsvector column for keyword search
- GIN index on JSONB metadata for filtered queries
- B-tree indexes on `routine_type`, `subroutine_name`, `file_path`, and `blas_level` for filtered queries

## Retrieval Pipeline

LegacyLens uses **hybrid search** combining vector similarity and keyword matching, fused with Reciprocal Rank Fusion (RRF), followed by optional LLM reranking.

### Query Flow

1. **Query Expansion** (opt-in, `expand=true`) — Claude Haiku rewrites the user query into 2–3 alternative phrasings to improve recall. The original query is always retained.

2. **Parallel Search** (6 concurrent workers via ThreadPoolExecutor):

   - **Vector Search** — Each query variant is embedded with the same model used during ingestion. The HNSW index returns the top-15 nearest neighbors by cosine similarity (top-10 if reranking is disabled). Results from all variants are pooled.

   - **Keyword Search** — PostgreSQL `plainto_tsquery` performs full-text search on the generated `tsvector` column, scored by `ts_rank`. Exact subroutine name matches receive a 10.0 weight boost. Returns top-10 results.

   Both searches respect filters: `routine_type`, `precision_type`, `blas_level`.

3. **Reciprocal Rank Fusion** — Vector and keyword results are merged using RRF with k=60 and query-type-aware weights:
   ```
   score(doc) = Σ  weight × 1 / (k + rank + 1)   for each retrieval method
   ```
   - **Routine lookups** (single routine name or exact match): vector_weight=1.0, keyword_weight=1.5
   - **Concept queries** (general questions): vector_weight=1.2, keyword_weight=1.0

4. **Concept Boosting** — Matching routines from the concept map are injected with a high score (999.0). Called routines from boosted results are also added (score 500.0, up to 5 additional). D-prefix routines (double precision drivers) receive a 2× multiplier; helper routines (names ending in a digit) receive a 0.5× penalty.

5. **Score Normalization** — RRF scores are normalized to a 0–1 range and assigned relevance labels: High (>0.7), Medium (>0.4), Low (≤0.4).

6. **LLM Reranking** (enabled by default, `rerank=true`) — Claude Haiku reranks the top-15 candidates by relevance to the query. The reranking prompt emphasizes primary/computational routines over helpers and exact name matches. Exact subroutine name matches are pinned at the front. Falls back to original ranking on any error.

7. **Metadata Filtering** — Users can filter by routine type (BLAS, driver, computational), BLAS level (1, 2, 3), and precision type (single, double, complex, double complex). Filters are applied as SQL `WHERE` clauses at both the vector and keyword search stages.

### Caching

- **Response cache** — LRU, max 512 entries. Key = hash(query, top_k, routine_type, precision_type, blas_level, expand, rerank).
- **Embedding cache** — LRU, max 256 entries. Key = SHA256(text). Avoids re-embedding repeated queries.
- **Understanding cache** — LRU, max 512 entries. Key = (routine_name, action). Caches code understanding results.

### Answer Generation

The top-5 retrieved chunks are passed as context to Claude Haiku 4.5, which generates a streaming answer via Server-Sent Events (SSE). The system prompt instructs the model to cite specific `[file:line]` references, explain code in plain English, and suggest related routines. A brief mode (256 max tokens vs. 512) is available for concise answers.

## Code Understanding Features

Beyond search, LegacyLens provides seven specialized analysis features, each accessible via action buttons on result cards or the browse tab:

| Feature | Endpoint | Method |
|---------|----------|--------|
| **Explain** | `POST /api/understand/explain` | Claude generates a plain-English explanation of a subroutine's purpose, parameters, algorithm, and use cases (768 max tokens) |
| **ELI5** | `POST /api/understand/eli5` | Claude generates a kid-friendly explanation with emojis (512 max tokens) |
| **Dependencies** | `POST /api/understand/dependencies` | BFS traversal of call chains using the `calls` metadata field, up to configurable depth (default 3) |
| **Similar** | `POST /api/understand/similar` | Finds routines with the most similar embeddings (cosine similarity), top-5 by default |
| **Documentation** | `POST /api/understand/document` | Claude generates structured docs with PURPOSE, PARAMETERS, ALGORITHM, RETURN VALUES, and DEPENDENCIES sections (1536 max tokens) |
| **Translate** | `POST /api/understand/translate` | Claude generates a Python/NumPy/SciPy equivalent with examples (1536 max tokens) |
| **Use Cases** | `POST /api/understand/use-cases` | Claude generates scenarios for when and why to use this routine (512 max tokens) |

All LLM-powered features use Claude Haiku 4.5, truncate code content to 6,000 characters, support fuzzy routine name matching, and are cached per (routine, action) pair.

## Visualization & Exploration

| Feature | Endpoint | Description |
|---------|----------|-------------|
| **Call Graph** | `GET /api/graph` | Force-directed graph of routine call relationships. Nodes colored by type (driver, computational, BLAS). Filterable by routine_type. |
| **Codebase Stats** | `GET /api/stats` | Summary cards (total routines, files, LOC), breakdowns by type and precision, top 10 largest and most-called routines |
| **Browse** | Frontend only | Alphabetical directory of all routines with type filters, search, and per-routine action buttons |

## Frontend

The Next.js frontend provides four tabs:

1. **Search** — Query input with expand/brief toggles, search filters, streaming answer display with citation validation, and result cards with file drill-down
2. **Map** — Interactive force-directed graph (react-force-graph-2d) with node search, hover tooltips, selection side panel, and color legend
3. **Stats** — Summary cards and breakdowns pulled from `/api/stats`
4. **Browse** — Alphabetical routine directory with type filters and per-routine actions (Explain, Translate, Deps, Similar)

Deep linking supports `?tab=search|map|stats|browse` and `?routine=DGESV&action=explain` for direct routine access.

## Technology Choices

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Vector DB | pgvector (Supabase) | SQL metadata filtering, generated tsvector for hybrid search, free tier |
| Embedding | text-embedding-3-small (1536d) | $0.02/1M tokens, sufficient quality for code retrieval, 8K context |
| LLM | Claude Haiku 4.5 | $1/$5 per 1M tokens, fast streaming, strong code comprehension |
| Chunking | Regex-based subroutine boundaries | Preserves semantic units; Fortran's rigid structure makes regex reliable |
| Search | Hybrid (vector + BM25 + RRF) + LLM rerank | Vector captures semantic similarity; keyword catches exact routine names; reranking improves precision |
| Caching | LRU (response, embedding, understanding) | Reduces latency and API costs for repeated queries |
| Frontend | Next.js 16 + React 19 on Vercel | Free hosting, fast deploys, SSE support, app router |
| Backend | FastAPI on Fly.io | Async SSE streaming, ThreadPoolExecutor for parallel search, Python ecosystem for LLM libraries |
| Visualization | react-force-graph-2d | Interactive force-directed layout for call graph exploration |

## Limitations and Future Work

- **Chunking granularity** — Whole-subroutine chunks can be large; sub-function splitting could improve precision for very long routines.
- **Embedding model** — Voyage code-3 (optimized for code) would likely improve retrieval quality at higher cost.
- **Call chain accuracy** — Dependency mapping relies on regex `CALL` extraction, which misses function-style calls and computed references.
- **No incremental indexing** — Re-ingestion requires a full rebuild; a delta-based approach would support codebase updates.
- **Reranking latency** — LLM reranking adds ~1–2s per query; a cross-encoder reranker could be faster at comparable quality.
