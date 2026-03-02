# LegacyLens - Technology Stack

## Architecture Overview

```
User Query -> Next.js Frontend -> FastAPI Backend -> LlamaIndex Pipeline
                                                          |
                                          +-----------+---+-----------+
                                          |           |               |
                                    OpenAI API   Supabase/pgvector  Claude API
                                   (Embeddings)  (Vector Storage)  (Answer Gen)
```

## Stack Decisions

| Layer | Technology | Version | Rationale |
|---|---|---|---|
| Target Codebase | LAPACK (Fortran) | v3.12.1 | Authentic legacy Fortran, 10:1 doc ratio, one-subroutine-per-file |
| Vector Database | pgvector via Supabase | pgvector 0.8+ | Full SQL metadata filtering, no idle suspension, complete free backend |
| Embedding Model | OpenAI text-embedding-3-small | - | $0.02/1M tokens, 1536 dims, 8K context, best cost/value for MVP |
| Embedding Upgrade | Voyage code-3 | - | $0.18/1M tokens, 1024 dims, 32K context, 92% code retrieval score |
| LLM (Primary) | Claude Haiku 4.5 | claude-haiku-4-5-20251001 | $1/$5 per 1M tokens, fast, good code understanding |
| LLM (Complex) | Claude Sonnet 4.6 | claude-sonnet-4-6 | $3/$15 per 1M tokens, deep architectural analysis |
| RAG Framework | LlamaIndex | latest | AST-based CodeSplitter (tree-sitter), best retrieval quality |
| Backend | Python / FastAPI | 3.11+ / 0.100+ | LlamaIndex is Python-native, FastAPI is lightweight and async |
| Frontend | Next.js | 14+ | Free Vercel hosting, fast deployment, good DX |
| Deployment (FE) | Vercel | - | Free tier, automatic HTTPS, edge network |
| Deployment (BE) | Railway or Render | - | Free tier for backend API hosting |
| Deployment (DB) | Supabase | - | Free tier: 500 MB storage, REST API, auth included |

## Key Dependencies

### Backend (Python)
```
llama-index
llama-index-vector-stores-postgres
llama-index-embeddings-openai
fastapi
uvicorn
anthropic
openai
supabase
psycopg2-binary
tree-sitter
tree-sitter-fortran
python-dotenv
```

### Frontend (Node.js)
```
next
react
tailwindcss
@supabase/supabase-js (if direct DB access needed)
```

## Environment Variables

```env
# Embeddings
OPENAI_API_KEY=

# LLM Answer Generation
ANTHROPIC_API_KEY=

# Database
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=
DATABASE_URL=          # Direct Postgres connection string

# Optional
VOYAGE_API_KEY=        # If upgrading to Voyage code-3
```

## Database Schema (pgvector)

```sql
-- Code chunks with embeddings
CREATE TABLE code_chunks (
    id BIGSERIAL PRIMARY KEY,
    file_path TEXT NOT NULL,
    line_start INTEGER NOT NULL,
    line_end INTEGER NOT NULL,
    subroutine_name TEXT,
    routine_type TEXT,           -- driver, computational, auxiliary, blas
    precision_type TEXT,         -- single, double, complex, double_complex
    content TEXT NOT NULL,       -- raw code text
    metadata JSONB,             -- additional structured metadata
    embedding VECTOR(1536),     -- OpenAI small dimensions
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- HNSW index for fast approximate nearest neighbor search
CREATE INDEX ON code_chunks
    USING hnsw (embedding vector_cosine_ops);

-- GIN index for metadata filtering
CREATE INDEX ON code_chunks USING GIN (metadata);

-- B-tree indexes for common filters
CREATE INDEX ON code_chunks (routine_type);
CREATE INDEX ON code_chunks (subroutine_name);
CREATE INDEX ON code_chunks (file_path);

-- Full-text search index for hybrid search
ALTER TABLE code_chunks ADD COLUMN fts TSVECTOR
    GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;
CREATE INDEX ON code_chunks USING GIN (fts);
```

## Cost Estimates

| Scale | Monthly Cost |
|---|---|
| Development / Demo | ~$10-25 total |
| 100 users (5 queries/day) | ~$8/month |
| 1,000 users | ~$55/month |
| 10,000 users | ~$500/month |
| 100,000 users | ~$5,000/month |
