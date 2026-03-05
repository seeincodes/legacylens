# LegacyLens

RAG-powered search and understanding for the LAPACK Fortran codebase. Ask natural language questions about 2,294 Fortran files and 977K lines of linear algebra code.

## Live Demo

- **Frontend:** [https://lapacklegacy-seeincodes.vercel.app/](https://lapacklegacy-seeincodes.vercel.app/)
- **Backend API:** [legacylens-api.fly.dev](https://legacylens-api.fly.dev)

## Documentation

- [RAG Architecture](docs/RAG_ARCHITECTURE.md) — System design, retrieval pipeline, technology choices
- [AI Cost Analysis](docs/AI_COST_ANALYSIS.md) — Development spend, per-query costs, production projections
- [Failure Modes](docs/FAILURE_MODES.md) — Known edge cases and retrieval failure analysis
- [Tech Stack](TECH_STACK.md) — Detailed technology decisions and schema
- [PRD](PRD.md) — Product requirements and scope

## Features

- **Hybrid Search** — Vector similarity (pgvector HNSW) + full-text keyword search (PostgreSQL tsvector) fused with Reciprocal Rank Fusion, returning normalized 0–1 relevance scores
- **LLM Reranking** — Claude Haiku reranks top-15 candidates by relevance (enabled by default), with concept boosting and exact-match pinning
- **Streaming Answers** — Claude Haiku generates explanations with inline `[SRC/file.f:line-line]` citations streamed via Server-Sent Events
- **Query Expansion** — Optional LLM-powered rephrasing into 2–3 query variants for higher recall
- **Code Understanding** — 7 per-routine actions: Explain, ELI5, Dependency tracing (list + interactive graph), Similar routine search, Documentation generation, Translate (Python/NumPy equivalent), Use Cases (when to use this routine)
- **Interactive Call Graph** — Force-directed graph visualization of routine call relationships, with node search, type filtering, and selection details
- **Codebase Stats** — Summary cards showing total routines, files, LOC, breakdowns by type and precision, and top 10 largest/most-called routines
- **Browse Directory** — Alphabetical directory of all routines with type filters, search, and per-routine action buttons
- **Metadata Filtering** — Filter by routine type (BLAS, driver, computational), BLAS level (1: vector, 2: matrix-vector, 3: matrix-matrix), and precision (single, double, complex)
- **Fortran Syntax Highlighting** — Custom tokenizer for Fortran keywords, strings, numbers, and comments
- **Evaluation Suite** — 25-query ground truth benchmark measuring Precision@K, Recall@K, MRR, and per-query latency

The frontend is organized into four tabs: **Search**, **Map** (call graph), **Stats**, and **Browse**. Deep linking via `?tab=` and `?routine=DGESV&action=explain` is supported.

## Architecture & Cost

LegacyLens uses a hybrid RAG pipeline: queries are embedded with OpenAI `text-embedding-3-small`, searched via pgvector (HNSW) + PostgreSQL full-text search, fused with Reciprocal Rank Fusion, reranked by Claude Haiku, and answered with streaming LLM generation citing specific `[file:line]` references.

```
User Query → Next.js (Vercel) → FastAPI (Fly.io) → OpenAI Embeddings
                                       ↓                    ↓
                                 Claude Haiku ← Supabase/pgvector
                                 (rerank +      (hybrid search +
                                  stream)        concept boost)
```

| Metric            | Value                  |
| ----------------- | ---------------------- |
| Codebase indexed  | 2,294 files / 977K LOC |
| Ingestion cost    | ~$0.10 (one-time)      |
| Per-query cost    | ~$0.006 (with rerank)  |
| Retrieval latency | ~2–5s median           |
| Total dev spend   | ~$3.13                 |

Full details: [RAG Architecture](docs/RAG_ARCHITECTURE.md) | [AI Cost Analysis](docs/AI_COST_ANALYSIS.md)

## BLAS Coverage

LegacyLens indexes the complete Reference BLAS implementation (159 files) alongside LAPACK core routines. BLAS routines are classified by level:

| Level       | Operations    | Examples                    | Count |
| ----------- | ------------- | --------------------------- | ----- |
| **Level 1** | Vector-vector | AXPY, DOT, SCAL, NRM2, SWAP | ~50   |
| **Level 2** | Matrix-vector | GEMV, TRSV, SYMV, GER       | ~65   |
| **Level 3** | Matrix-matrix | GEMM, TRSM, SYMM, SYRK      | ~25   |

Filter by BLAS level in the UI when "BLAS" is selected as routine type.

## Tech Stack

| Layer      | Technology                              |
| ---------- | --------------------------------------- |
| Frontend   | Next.js 16, React 19, Tailwind CSS 4    |
| Backend    | Python 3.12, FastAPI, Uvicorn           |
| Database   | PostgreSQL + pgvector (Supabase)        |
| Embeddings | OpenAI text-embedding-3-small (1536d)   |
| LLM        | Claude Haiku 4.5                        |
| Deployment | Vercel (FE), Fly.io (BE), Supabase (DB) |

## Local Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL with pgvector extension (or a Supabase project)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Copy and fill in environment variables
cp .env.example .env

# Set up database schema
psql $DATABASE_URL < scripts/setup_db.sql

# Download and ingest LAPACK source (one-time)
bash scripts/download_lapack.sh
python scripts/ingest.py

# Start server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install

# Set backend URL
echo 'NEXT_PUBLIC_API_URL=http://localhost:8000' > .env.local

npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### Environment Variables

| Variable            | Required | Description                                  |
| ------------------- | -------- | -------------------------------------------- |
| `OPENAI_API_KEY`    | Yes      | For embedding generation                     |
| `ANTHROPIC_API_KEY` | Yes      | For answer generation and code understanding |
| `DATABASE_URL`      | Yes      | PostgreSQL connection string with pgvector   |

## API Endpoints

| Method | Path                           | Description                              |
| ------ | ------------------------------ | ---------------------------------------- |
| `POST` | `/api/query`                   | Streaming search + answer (SSE)          |
| `POST` | `/api/query/sync`              | Non-streaming search + answer            |
| `GET`  | `/api/file/{file_path}`        | Get full file content by path            |
| `GET`  | `/api/graph`                   | Call graph data (nodes + links)          |
| `GET`  | `/api/stats`                   | Codebase statistics and breakdowns       |
| `POST` | `/api/understand/explain`      | Explain a subroutine                     |
| `POST` | `/api/understand/eli5`         | ELI5 explanation (kid-friendly + emojis) |
| `POST` | `/api/understand/dependencies` | Trace call dependency chains             |
| `POST` | `/api/understand/similar`      | Find similar routines by embedding       |
| `POST` | `/api/understand/document`     | Generate structured documentation        |
| `POST` | `/api/understand/translate`    | Generate Python/NumPy equivalent         |
| `POST` | `/api/understand/use-cases`    | Get use case scenarios                   |
| `GET`  | `/api/health`                  | Health check                             |

## Evaluation

Run the retrieval eval suite against the 25-query ground truth:

```bash
cd backend
python -m eval.run_eval                    # default top-5 (no expand/rerank)
python -m eval.run_eval --expand --rerank # recommended: query expansion + LLM rerank
python -m eval.run_eval --top-k 10         # evaluate at top-10
```

Metrics: Precision@K, Recall@K, MRR, Hit Rate, per-category breakdown, and latency percentiles.

Run the **RAG answer pipeline** eval (20 golden queries, full retrieval + generation):

```bash
cd backend
python -m eval.run_rag_eval                    # full RAG eval
python -m eval.run_rag_eval --expand --rerank  # with query expansion + rerank
python -m eval.run_rag_eval --output results.json
```

Metrics: fact pass rate, citation validity, retrieval hit rate, full pass rate, latency per query.

## Performance

| Metric              | Result                                                                  |
| ------------------- | ----------------------------------------------------------------------- |
| Retrieval latency   | ~2–5s median (p95 ~6s with expand+rerank) — embedding + DB + LLM rerank |
| Answer generation   | 5–30s streaming — depends on LLM response length                        |
| Retrieval precision | ~65–69% Precision@5 (expand+rerank, target >70%)                        |
| Codebase coverage   | 2,294 files / 977K LOC indexed                                          |
| Answer citations    | Correct file paths and line ranges                                      |
| Per-query cost      | ~$0.006 (with rerank), ~$0.004 (without)                                |
