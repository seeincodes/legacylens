# LegacyLens Design Document

**Date:** 2026-03-02
**Status:** Approved

## Summary

LegacyLens is a RAG-powered system that indexes the LAPACK Fortran codebase (~670 files, ~100K LOC) and provides a web interface for natural language querying. Users type questions like "How does LAPACK solve a system of linear equations?" and receive LLM-generated answers with cited code snippets.

## Architecture

Full-stack application with separate frontend and backend:

- **Frontend:** Next.js on Vercel -- single-page query interface with streaming answers
- **Backend:** Python FastAPI on Railway -- RAG pipeline (embed, search, generate)
- **Database:** Supabase pgvector -- vector storage with SQL metadata filtering
- **Embeddings:** OpenAI text-embedding-3-small (1536 dims)
- **LLM:** Claude Haiku 4.5 (streaming answers)

## Project Structure

```
legacylens/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point + CORS
│   │   ├── config.py            # Settings from env vars
│   │   ├── routers/
│   │   │   └── query.py         # API endpoints
│   │   ├── services/
│   │   │   ├── ingestion.py     # Chunking, embedding, storage
│   │   │   ├── retrieval.py     # Vector + BM25 search, RRF fusion
│   │   │   └── generation.py    # Claude prompt + streaming
│   │   └── models/
│   │       └── schemas.py       # Pydantic models
│   ├── scripts/
│   │   └── ingest.py            # One-time ingestion CLI
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # Query interface
│   │   └── layout.tsx           # Root layout
│   ├── components/
│   │   ├── QueryInput.tsx
│   │   ├── ResultsList.tsx
│   │   ├── CodeBlock.tsx
│   │   └── AnswerPanel.tsx
│   ├── package.json
│   └── next.config.js
├── data/lapack/                 # Gitignored LAPACK source
├── .env.example
├── .gitignore
└── README.md
```

## Data Flow

### Ingestion (one-time)
1. Download LAPACK double-precision `SRC/` + `BLAS/SRC/`
2. Scan for `.f` and `.f90` files
3. Parse subroutine boundaries via tree-sitter (or regex fallback)
4. Extract metadata: file path, line range, subroutine name, routine type, precision, CALL targets
5. Prepend metadata as text prefix to each chunk
6. Batch embed via OpenAI text-embedding-3-small
7. Insert into Supabase pgvector with metadata columns

### Query (runtime)
1. `POST /api/query` receives natural language query + optional filters
2. Embed query with same OpenAI model
3. Vector similarity search (pgvector HNSW, k=10)
4. BM25 keyword search (tsvector) for exact identifiers
5. RRF fusion to merge results, select top-5
6. Assemble prompt with retrieved code context
7. Stream Claude Haiku 4.5 response via SSE
8. Return streaming answer + chunk metadata

## API Endpoints

- `POST /api/query` -- Main query endpoint (streaming SSE response)
- `GET /api/file/{path}` -- Full file content for drill-down
- `GET /api/health` -- Status check

## Key Decisions

All decisions documented in PRE-SEARCH.md:
- pgvector over Pinecone/Qdrant (SQL filtering, no idle suspension)
- OpenAI small over Voyage code-3 (cost for MVP, upgrade path exists)
- LlamaIndex over LangChain (AST-based code splitting)
- Claude Haiku over GPT-4o-mini (better code understanding benchmarks)
- LAPACK over GnuCOBOL (authentic Fortran, not a C compiler)
