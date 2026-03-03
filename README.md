# LegacyLens

RAG-powered search and understanding for the LAPACK Fortran codebase. Ask natural language questions about ~670 Fortran files and 100K+ lines of linear algebra code.

## Live Demo

- **Frontend:** [frontend-nine-alpha-70.vercel.app](https://frontend-nine-alpha-70.vercel.app)
- **Backend API:** [legacylens-api.fly.dev](https://legacylens-api.fly.dev)

## Features

- **Hybrid Search** — Vector similarity (pgvector HNSW) + keyword search (PostgreSQL tsvector) merged with Reciprocal Rank Fusion
- **Streaming Answers** — Claude Haiku generates explanations with `[file:line]` citations via Server-Sent Events
- **Query Expansion** — LLM rephrases queries into multiple variants for better recall
- **Code Understanding** — Explain routines, trace dependency chains, find similar code, generate documentation
- **Metadata Filtering** — Filter by routine type (BLAS, driver, computational) and precision (single, double, complex)
- **Fortran Syntax Highlighting** — Custom tokenizer for Fortran keywords, strings, numbers, and comments

## Architecture

```
User Query → Next.js (Vercel) → FastAPI (Fly.io) → OpenAI Embeddings
                                        ↓                    ↓
                                  Claude Haiku ← Supabase/pgvector
                                  (streaming)    (hybrid search)
```

See [docs/RAG_ARCHITECTURE.md](docs/RAG_ARCHITECTURE.md) for full details.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, Tailwind CSS 4 |
| Backend | Python 3.11, FastAPI, Uvicorn |
| Database | PostgreSQL + pgvector (Supabase) |
| Embeddings | OpenAI text-embedding-3-small (1536d) |
| LLM | Claude Haiku 4.5 |
| Deployment | Vercel (FE), Fly.io (BE), Supabase (DB) |

## Local Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL with pgvector extension (or a Supabase project)

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Copy and fill in environment variables
cp .env.example .env

# Set up database schema
psql $DATABASE_URL < scripts/setup_db.sql

# Ingest LAPACK source (one-time)
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

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | For embedding generation |
| `ANTHROPIC_API_KEY` | Yes | For answer generation and code understanding |
| `DATABASE_URL` | Yes | PostgreSQL connection string with pgvector |
| `SUPABASE_URL` | No | Supabase project URL |
| `SUPABASE_ANON_KEY` | No | Supabase anonymous key |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/query` | Streaming search + answer (SSE) |
| `POST` | `/api/query/sync` | Non-streaming search + answer |
| `GET` | `/api/file` | Get full file content |
| `POST` | `/api/understand/explain` | Explain a subroutine |
| `POST` | `/api/understand/dependencies` | Trace call chains |
| `POST` | `/api/understand/similar` | Find similar routines |
| `POST` | `/api/understand/document` | Generate documentation |
| `GET` | `/api/health` | Health check |

## Documentation

- [RAG Architecture](docs/RAG_ARCHITECTURE.md) — System design, retrieval pipeline, technology choices
- [AI Cost Analysis](docs/AI_COST_ANALYSIS.md) — Development spend, per-query costs, production projections
- [Tech Stack](TECH_STACK.md) — Detailed technology decisions and schema
- [PRD](PRD.md) — Product requirements and scope

## Cost

- **Development total:** ~$2.14
- **Per query:** ~$0.004–0.005
- **100 users at 5 queries/day:** ~$60/month

See [docs/AI_COST_ANALYSIS.md](docs/AI_COST_ANALYSIS.md) for full breakdown.
