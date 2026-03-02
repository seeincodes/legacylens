-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Code chunks with embeddings
CREATE TABLE IF NOT EXISTS code_chunks (
    id BIGSERIAL PRIMARY KEY,
    file_path TEXT NOT NULL,
    line_start INTEGER NOT NULL,
    line_end INTEGER NOT NULL,
    subroutine_name TEXT,
    routine_type TEXT,
    precision_type TEXT,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    embedding VECTOR(1536),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Full-text search column
ALTER TABLE code_chunks ADD COLUMN IF NOT EXISTS fts TSVECTOR
    GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON code_chunks
    USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_chunks_fts ON code_chunks USING GIN (fts);
CREATE INDEX IF NOT EXISTS idx_chunks_metadata ON code_chunks USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_chunks_routine_type ON code_chunks (routine_type);
CREATE INDEX IF NOT EXISTS idx_chunks_subroutine ON code_chunks (subroutine_name);
CREATE INDEX IF NOT EXISTS idx_chunks_file_path ON code_chunks (file_path);
