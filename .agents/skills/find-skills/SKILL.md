# Skill: Find Skills

## Context
LegacyLens is a RAG system for querying the LAPACK Fortran codebase via natural language.

## Project Skills & Patterns

### Codebase
- **Target:** LAPACK (Fortran 77/90) -- double-precision routines from `SRC/` + `BLAS/SRC/`
- ~670 files, ~100K+ LOC
- One subroutine per file, 10:1 documentation-to-code ratio
- Naming convention: `XYYZZZ` (X=precision, YY=matrix type, ZZZ=operation)

### Stack
- **Vector DB:** pgvector via Supabase (SQL metadata filtering, hybrid search)
- **Embeddings:** OpenAI text-embedding-3-small (1536 dims, $0.02/1M tokens)
- **LLM:** Claude Haiku 4.5 (primary), Sonnet 4.6 (complex queries)
- **Framework:** LlamaIndex (AST-based CodeSplitter with tree-sitter)
- **Backend:** Python / FastAPI
- **Frontend:** Next.js on Vercel
- **Deployment:** Vercel + Railway + Supabase

### Key Files
- `PRE-SEARCH.md` -- Full technology comparison and architecture decisions
- `PRD.md` -- Product requirements and MVP checklist
- `TECH_STACK.md` -- Stack details, DB schema, dependencies, costs
- `TASK_LIST.md` -- Phased task breakdown (MVP -> Polish -> Final)
- `USER_FLOW.md` -- Query flow, API endpoints, example queries
- `MEMO.md` -- Architecture memo with decision rationale
- `ERROR_FIX_LOG.md` -- Error tracking and common gotchas

### Chunking Strategy
- Split by SUBROUTINE/FUNCTION boundaries
- Include comment header blocks in each chunk
- Prepend metadata as text prefix per chunk
- Target 500-1500 tokens per chunk

### Retrieval Pipeline
- Vector search (top-k=10) + BM25 keyword search
- RRF fusion, re-rank to top-5
- Context assembly with surrounding code
- Claude Haiku generates answer with [file:line] citations
