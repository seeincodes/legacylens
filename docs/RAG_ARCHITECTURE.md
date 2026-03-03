# LegacyLens — RAG Architecture Document

## System Overview

LegacyLens is a Retrieval-Augmented Generation (RAG) system that makes the LAPACK Fortran codebase (~670 files, 100K+ LOC) searchable and explainable through natural language. Users type questions like "What does DGESV do?" and receive relevant code snippets with LLM-generated explanations citing specific file paths and line numbers.

```
                         ┌─────────────────┐
  User Query ──────────► │  Next.js Front  │
                         │  (Vercel)       │
                         └────────┬────────┘
                                  │ POST /api/query (SSE stream)
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
     │  (Embed)     │   │  PostgreSQL  │   │  (Generate)  │
     │              │   │  + pgvector  │   │              │
     └──────────────┘   └──────────────┘   └──────────────┘
```

## Ingestion Pipeline

**Goal:** Convert raw Fortran source into searchable, embedded chunks.

1. **File Discovery** — Recursively scans `SRC/` and `BLAS/SRC/` for `.f` and `.f90` files.

2. **Syntax-Aware Chunking** — A regex-based Fortran parser extracts subroutine/function blocks by matching `SUBROUTINE`/`FUNCTION` definitions and their corresponding `END` statements. Each chunk includes its preceding comment block. Chunks that don't match a subroutine boundary fall back to the whole file.

3. **Metadata Extraction** — For each chunk:
   - **Precision type** inferred from filename prefix (`D`=double, `S`=single, `C`=complex, `Z`=double complex)
   - **Routine type** classified as `blas`, `driver`, or `computational` based on file path and call count heuristics
   - **Call chain** extracted via regex matching of `CALL` statements

4. **Embedding** — Each chunk is prefixed with its metadata (file path, routine name, type, precision) and embedded with OpenAI `text-embedding-3-small` (1536 dimensions). Texts are truncated at 15K characters. Batched in groups of 100.

5. **Storage** — Chunks, metadata (as JSONB), and embeddings are inserted into a PostgreSQL table with pgvector. A generated `tsvector` column enables full-text search.

**Indexes:**
- HNSW index on embeddings (cosine distance) for approximate nearest-neighbor search
- GIN index on the `fts` tsvector column for keyword search
- B-tree indexes on `routine_type`, `subroutine_name`, and `file_path` for filtered queries

## Retrieval Pipeline

LegacyLens uses **hybrid search** combining vector similarity and keyword matching, fused with Reciprocal Rank Fusion (RRF).

### Query Flow

1. **Query Expansion** (optional) — Claude Haiku rewrites the user query into 2-3 alternative phrasings to improve recall. The original query is always retained.

2. **Vector Search** — Each query variant is embedded with the same model used during ingestion. The HNSW index returns the top-10 nearest neighbors by cosine similarity. Results from all variants are pooled.

3. **Keyword Search** — PostgreSQL `plainto_tsquery` performs full-text search on the generated `tsvector` column, scored by `ts_rank`. Returns top-10 results.

4. **Reciprocal Rank Fusion** — Vector and keyword results are merged using RRF with k=60:
   ```
   score(doc) = Σ  1 / (k + rank + 1)   for each retrieval method
   ```
   This balances semantic relevance (vector) with exact-match precision (keyword).

5. **Score Normalization** — RRF scores are normalized to a 0–1 range and assigned relevance labels: High (>0.7), Medium (>0.4), Low (≤0.4).

6. **Metadata Filtering** — Users can filter by routine type (BLAS, driver, computational) and precision type (single, double, complex, double complex). Filters are applied as SQL `WHERE` clauses at both the vector and keyword search stages.

### Answer Generation

The top-5 retrieved chunks are passed as context to Claude Haiku 4.5, which generates a streaming answer via Server-Sent Events (SSE). The system prompt instructs the model to cite specific `[file:line]` references, explain code in plain English, and suggest related routines.

## Code Understanding Features

Beyond search, LegacyLens provides four specialized analysis features, each accessible via action buttons on search result cards:

| Feature | Endpoint | Method |
|---------|----------|--------|
| **Explain** | `POST /api/understand/explain` | Claude generates a plain-English explanation of a subroutine's purpose, parameters, algorithm, and use cases |
| **Dependencies** | `POST /api/understand/dependencies` | BFS traversal of call chains using the `calls` metadata field, up to configurable depth |
| **Similar** | `POST /api/understand/similar` | Finds routines with the most similar embeddings (cosine similarity), excluding the source routine |
| **Documentation** | `POST /api/understand/document` | Claude generates structured docs with PURPOSE, PARAMETERS, ALGORITHM, RETURN VALUES, and DEPENDENCIES sections |

## Technology Choices

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Vector DB | pgvector (Supabase) | SQL metadata filtering, generated tsvector for hybrid search, free tier |
| Embedding | text-embedding-3-small (1536d) | $0.02/1M tokens, sufficient quality for code retrieval, 8K context |
| LLM | Claude Haiku 4.5 | $1/$5 per 1M tokens, fast streaming, strong code comprehension |
| Chunking | Regex-based subroutine boundaries | Preserves semantic units; Fortran's rigid structure makes regex reliable |
| Search | Hybrid (vector + BM25 + RRF) | Vector captures semantic similarity; keyword catches exact routine names |
| Frontend | Next.js on Vercel | Free hosting, fast deploys, SSE support |
| Backend | FastAPI on Fly.io | Async SSE streaming, lightweight, Python ecosystem for LLM libraries |

## Limitations and Future Work

- **Chunking granularity** — Whole-subroutine chunks can be large; sub-function splitting could improve precision for very long routines.
- **Embedding model** — Voyage code-3 (optimized for code) would likely improve retrieval quality at higher cost.
- **Call chain accuracy** — Dependency mapping relies on regex `CALL` extraction, which misses function-style calls and computed references.
- **No incremental indexing** — Re-ingestion requires a full rebuild; a delta-based approach would support codebase updates.
