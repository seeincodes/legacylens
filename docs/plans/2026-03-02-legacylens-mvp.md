# LegacyLens MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a working RAG system that indexes the LAPACK Fortran codebase and provides a web interface for natural language querying with LLM-generated answers.

**Architecture:** Full-stack app -- Next.js frontend on Vercel, FastAPI backend on Railway, Supabase pgvector for vector storage. Ingestion script chunks Fortran by subroutine boundaries, embeds via OpenAI, stores in pgvector. Query pipeline does vector + BM25 hybrid search, assembles context, streams Claude Haiku answers.

**Tech Stack:** Python 3.11+, FastAPI, LlamaIndex, OpenAI text-embedding-3-small, Claude Haiku 4.5, Supabase pgvector, Next.js 14+, Tailwind CSS, Vercel, Railway.

**Reference docs:** `PRE-SEARCH.md`, `TECH_STACK.md`, `PRD.md`, `USER_FLOW.md`, `MEMO.md`

---

## Task 1: Initialize Git Repo and Project Structure

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `README.md`
- Create: directory structure for `backend/` and `frontend/`

**Step 1: Initialize git**

```bash
cd /Users/xian/legacylens
git init
```

**Step 2: Create `.gitignore`**

```gitignore
# Environment
.env
.env.local
.env.production

# Python
__pycache__/
*.pyc
.venv/
venv/

# Node
node_modules/
.next/

# Data
data/lapack/

# OS
.DS_Store
```

**Step 3: Create `.env.example`**

```env
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=
DATABASE_URL=
```

**Step 4: Create directory structure**

```bash
mkdir -p backend/app/routers backend/app/services backend/app/models backend/scripts backend/tests
mkdir -p frontend
mkdir -p data
```

**Step 5: Commit**

```bash
git add .gitignore .env.example README.md
git add backend/ frontend/ data/ docs/
git add PRE-SEARCH.md PRD.md TECH_STACK.md TASK_LIST.md USER_FLOW.md MEMO.md ERROR_FIX_LOG.md
git add .agents/ .cursor/
git commit -m "feat: initialize project structure and planning docs"
```

---

## Task 2: Set Up Python Backend

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/schemas.py`
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/query.py`
- Create: `backend/app/services/__init__.py`

**Step 1: Create `backend/requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
python-dotenv==1.0.1
openai==1.50.0
anthropic==0.39.0
psycopg2-binary==2.9.9
asyncpg==0.29.0
sqlalchemy==2.0.35
pgvector==0.3.5
pydantic==2.9.0
pydantic-settings==2.5.0
sse-starlette==2.1.0
```

Note: We use `openai` + `anthropic` + `pgvector` + `psycopg2` directly instead of the full LlamaIndex stack. This keeps dependencies minimal and gives us full control over the pipeline. If tree-sitter Fortran parsing proves necessary, add `tree-sitter` and `tree-sitter-fortran` later.

**Step 2: Create `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    anthropic_api_key: str
    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str
    database_url: str

    class Config:
        env_file = ".env"


settings = Settings()
```

**Step 3: Create `backend/app/models/schemas.py`**

```python
from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    routine_type: str | None = None


class ChunkResult(BaseModel):
    file_path: str
    line_start: int
    line_end: int
    subroutine_name: str | None
    routine_type: str | None
    content: str
    relevance_score: float


class QueryResponse(BaseModel):
    answer: str
    chunks: list[ChunkResult]
```

**Step 4: Create `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import query

app = FastAPI(title="LegacyLens", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

**Step 5: Create `backend/app/routers/query.py`** (stub)

```python
from fastapi import APIRouter
from app.models.schemas import QueryRequest, QueryResponse

router = APIRouter()


@router.post("/query")
async def query_codebase(request: QueryRequest):
    return {"answer": "Not implemented yet", "chunks": []}
```

**Step 6: Create empty `__init__.py` files**

Create empty files at:
- `backend/app/__init__.py`
- `backend/app/models/__init__.py`
- `backend/app/routers/__init__.py`
- `backend/app/services/__init__.py`

**Step 7: Set up virtual environment and test the server starts**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
```

Run: `cd backend && python -m uvicorn app.main:app --reload --port 8000`
Expected: Server starts, `http://localhost:8000/api/health` returns `{"status":"ok"}`

**Step 8: Commit**

```bash
git add backend/
git commit -m "feat: scaffold FastAPI backend with config, schemas, and health endpoint"
```

---

## Task 3: Set Up Supabase Database

**Files:**
- Create: `backend/scripts/setup_db.sql`

**Step 1: Create the SQL schema file**

```sql
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
```

**Step 2: Run the schema on Supabase**

Go to Supabase dashboard -> SQL Editor -> paste and run `setup_db.sql`.
Or run via CLI:
```bash
psql "$DATABASE_URL" -f backend/scripts/setup_db.sql
```

Expected: Tables and indexes created without errors.

**Step 3: Verify by querying**

```bash
psql "$DATABASE_URL" -c "SELECT count(*) FROM code_chunks;"
```
Expected: `count = 0`

**Step 4: Commit**

```bash
git add backend/scripts/setup_db.sql
git commit -m "feat: add pgvector database schema for code chunks"
```

---

## Task 4: Download LAPACK Source

**Files:**
- Create: `backend/scripts/download_lapack.sh`

**Step 1: Create download script**

```bash
#!/bin/bash
set -e

DATA_DIR="$(dirname "$0")/../../data/lapack"
mkdir -p "$DATA_DIR"

if [ -d "$DATA_DIR/SRC" ]; then
    echo "LAPACK already downloaded at $DATA_DIR"
    exit 0
fi

echo "Downloading LAPACK v3.12.1..."
curl -L https://github.com/Reference-LAPACK/lapack/archive/refs/tags/v3.12.1.tar.gz -o /tmp/lapack.tar.gz

echo "Extracting..."
tar -xzf /tmp/lapack.tar.gz -C /tmp

echo "Copying SRC/ and BLAS/SRC/..."
cp -r /tmp/lapack-3.12.1/SRC "$DATA_DIR/SRC"
cp -r /tmp/lapack-3.12.1/BLAS "$DATA_DIR/BLAS"

echo "Cleaning up..."
rm -rf /tmp/lapack.tar.gz /tmp/lapack-3.12.1

FILE_COUNT=$(find "$DATA_DIR" -name "*.f" -o -name "*.f90" | wc -l)
echo "Done. Found $FILE_COUNT Fortran files."
```

**Step 2: Run it**

```bash
chmod +x backend/scripts/download_lapack.sh
bash backend/scripts/download_lapack.sh
```

Expected: `Done. Found ~2200+ Fortran files.` (all precision variants; we'll filter to double-precision during ingestion)

**Step 3: Verify**

```bash
ls data/lapack/SRC/dgesv.f
ls data/lapack/BLAS/SRC/dgemm.f
```
Expected: Both files exist.

**Step 4: Commit**

```bash
git add backend/scripts/download_lapack.sh
git commit -m "feat: add LAPACK download script"
```

---

## Task 5: Build Fortran Chunking and Ingestion Service

**Files:**
- Create: `backend/app/services/ingestion.py`
- Create: `backend/tests/test_ingestion.py`

**Step 1: Write tests for the Fortran parser**

```python
# backend/tests/test_ingestion.py
from app.services.ingestion import parse_fortran_file, extract_metadata

SAMPLE_FORTRAN = """\
*> \\brief <b> DGESV computes the solution to system of linear equations A * X = B</b>
*
*  Purpose
*  =======
*  DGESV computes the solution to a real system of linear equations
*     A * X = B,
*  where A is an N-by-N matrix and X and B are N-by-NRHS matrices.
*
      SUBROUTINE DGESV( N, NRHS, A, LDA, IPIV, B, LDB, INFO )
*
*     .. Scalar Arguments ..
      INTEGER            INFO, LDA, LDB, N, NRHS
*     ..
*     .. Array Arguments ..
      INTEGER            IPIV( * )
      DOUBLE PRECISION   A( LDA, * ), B( LDB, * )
*
      EXTERNAL           DGETRF, DGETRS
*
      CALL DGETRF( N, N, A, LDA, IPIV, INFO )
      CALL DGETRS( 'No transpose', N, NRHS, A, LDA, IPIV, B, LDB, INFO )
*
      RETURN
      END
"""


def test_parse_fortran_extracts_subroutine():
    chunks = parse_fortran_file(SAMPLE_FORTRAN, "SRC/dgesv.f")
    assert len(chunks) >= 1
    assert chunks[0]["subroutine_name"] == "DGESV"


def test_extract_metadata_gets_calls():
    meta = extract_metadata(SAMPLE_FORTRAN, "SRC/dgesv.f")
    assert "DGETRF" in meta["calls"]
    assert "DGETRS" in meta["calls"]


def test_extract_metadata_detects_precision():
    meta = extract_metadata(SAMPLE_FORTRAN, "SRC/dgesv.f")
    assert meta["precision_type"] == "double"


def test_parse_filters_double_precision():
    chunks = parse_fortran_file(SAMPLE_FORTRAN, "SRC/dgesv.f")
    # File starts with 'd' -> double precision, should be included
    assert len(chunks) >= 1

    # A single-precision file should still parse but metadata reflects that
    chunks_s = parse_fortran_file(SAMPLE_FORTRAN, "SRC/sgesv.f")
    assert chunks_s[0]["precision_type"] == "single"
```

**Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_ingestion.py -v
```
Expected: FAIL -- `ImportError: cannot import name 'parse_fortran_file'`

**Step 3: Implement the ingestion service**

```python
# backend/app/services/ingestion.py
import os
import re
from pathlib import Path

import openai
import psycopg2
from pgvector.psycopg2 import register_vector

from app.config import settings

# Regex patterns for Fortran parsing
SUBROUTINE_RE = re.compile(
    r"^\s+(SUBROUTINE|(?:[\w*]+\s+)?FUNCTION)\s+(\w+)\s*\(",
    re.MULTILINE | re.IGNORECASE,
)
END_RE = re.compile(
    r"^\s+END\s*(SUBROUTINE|FUNCTION)?\s*(\w*)\s*$",
    re.MULTILINE | re.IGNORECASE,
)
CALL_RE = re.compile(r"CALL\s+(\w+)", re.IGNORECASE)
PRECISION_MAP = {
    "s": "single",
    "d": "double",
    "c": "complex",
    "z": "double_complex",
}


def detect_precision(file_path: str) -> str:
    basename = Path(file_path).stem.lower()
    if basename and basename[0] in PRECISION_MAP:
        return PRECISION_MAP[basename[0]]
    return "unknown"


def detect_routine_type(content: str, file_path: str) -> str:
    path_lower = file_path.lower()
    if "blas" in path_lower:
        return "blas"
    # LAPACK driver routines typically call both factorization and solve
    content_upper = content.upper()
    # Simple heuristic: if it has EXTERNAL declarations with multiple routines
    if "DRIVER" in content_upper or (
        content_upper.count("CALL ") >= 3
    ):
        return "driver"
    if "AUXILIARY" in content_upper:
        return "auxiliary"
    return "computational"


def extract_metadata(content: str, file_path: str) -> dict:
    calls = [m.group(1).upper() for m in CALL_RE.finditer(content)]
    return {
        "file_path": file_path,
        "precision_type": detect_precision(file_path),
        "routine_type": detect_routine_type(content, file_path),
        "calls": list(set(calls)),
    }


def parse_fortran_file(content: str, file_path: str) -> list[dict]:
    """Parse a Fortran file into chunks by subroutine/function boundaries."""
    meta = extract_metadata(content, file_path)
    lines = content.split("\n")

    # Find subroutine/function boundaries
    chunks = []
    current_name = None
    current_start = 0

    for i, line in enumerate(lines):
        sub_match = SUBROUTINE_RE.match(line)
        if sub_match:
            current_name = sub_match.group(2).upper()
            current_start = i

        end_match = END_RE.match(line)
        if end_match and current_name:
            chunk_content = "\n".join(lines[current_start : i + 1])
            # Include preceding comment block (scan backwards from current_start)
            comment_start = current_start
            for j in range(current_start - 1, -1, -1):
                stripped = lines[j].strip()
                if stripped.startswith("*") or stripped.startswith("!") or stripped == "":
                    comment_start = j
                else:
                    break
            if comment_start < current_start:
                chunk_content = "\n".join(lines[comment_start : i + 1])
                current_start = comment_start

            chunks.append({
                "file_path": file_path,
                "line_start": current_start + 1,
                "line_end": i + 1,
                "subroutine_name": current_name,
                "routine_type": meta["routine_type"],
                "precision_type": meta["precision_type"],
                "content": chunk_content,
                "metadata": {
                    "calls": meta["calls"],
                },
            })
            current_name = None

    # If no subroutine found, treat entire file as one chunk
    if not chunks:
        basename = Path(file_path).stem.upper()
        chunks.append({
            "file_path": file_path,
            "line_start": 1,
            "line_end": len(lines),
            "subroutine_name": basename,
            "routine_type": meta["routine_type"],
            "precision_type": meta["precision_type"],
            "content": content,
            "metadata": {"calls": meta["calls"]},
        })

    return chunks


def discover_fortran_files(base_dir: str) -> list[str]:
    """Recursively find all .f and .f90 files."""
    files = []
    for root, _, filenames in os.walk(base_dir):
        for f in filenames:
            if f.endswith((".f", ".f90")):
                files.append(os.path.join(root, f))
    return sorted(files)


def build_chunk_text(chunk: dict) -> str:
    """Prepend metadata prefix to chunk content for embedding."""
    prefix = (
        f"File: {chunk['file_path']} | "
        f"Subroutine: {chunk['subroutine_name']} | "
        f"Type: {chunk['routine_type']} | "
        f"Precision: {chunk['precision_type']}"
    )
    return f"{prefix}\n\n{chunk['content']}"


def generate_embeddings(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    """Generate embeddings via OpenAI API in batches."""
    client = openai.OpenAI(api_key=settings.openai_api_key)
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=batch,
        )
        all_embeddings.extend([item.embedding for item in response.data])
        print(f"  Embedded {min(i + batch_size, len(texts))}/{len(texts)}")

    return all_embeddings


def store_chunks(chunks: list[dict], embeddings: list[list[float]]):
    """Insert chunks and embeddings into pgvector."""
    conn = psycopg2.connect(settings.database_url)
    register_vector(conn)
    cur = conn.cursor()

    for chunk, emb in zip(chunks, embeddings):
        cur.execute(
            """
            INSERT INTO code_chunks
                (file_path, line_start, line_end, subroutine_name,
                 routine_type, precision_type, content, metadata, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                chunk["file_path"],
                chunk["line_start"],
                chunk["line_end"],
                chunk["subroutine_name"],
                chunk["routine_type"],
                chunk["precision_type"],
                chunk["content"],
                psycopg2.extras.Json(chunk["metadata"]),
                emb,
            ),
        )

    conn.commit()
    cur.close()
    conn.close()
```

**Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_ingestion.py -v
```
Expected: All 4 tests PASS.

**Step 5: Commit**

```bash
git add backend/app/services/ingestion.py backend/tests/test_ingestion.py
git commit -m "feat: add Fortran parser and ingestion service with tests"
```

---

## Task 6: Build the Ingestion Script

**Files:**
- Create: `backend/scripts/ingest.py`

**Step 1: Create the ingestion script**

```python
#!/usr/bin/env python3
"""One-time script to ingest LAPACK source into pgvector."""
import sys
import os
import time

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from app.services.ingestion import (
    discover_fortran_files,
    parse_fortran_file,
    build_chunk_text,
    generate_embeddings,
    store_chunks,
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "lapack")


def main():
    print("=== LegacyLens Ingestion ===\n")

    # Discover files
    src_dir = os.path.join(DATA_DIR, "SRC")
    blas_dir = os.path.join(DATA_DIR, "BLAS", "SRC")

    files = []
    if os.path.isdir(src_dir):
        files.extend(discover_fortran_files(src_dir))
    if os.path.isdir(blas_dir):
        files.extend(discover_fortran_files(blas_dir))

    if not files:
        print(f"ERROR: No Fortran files found. Run download_lapack.sh first.")
        print(f"  Looked in: {src_dir}")
        print(f"  Looked in: {blas_dir}")
        sys.exit(1)

    print(f"Found {len(files)} Fortran files")

    # Parse all files into chunks
    all_chunks = []
    for fpath in files:
        rel_path = os.path.relpath(fpath, DATA_DIR)
        with open(fpath, "r", errors="replace") as f:
            content = f.read()
        chunks = parse_fortran_file(content, rel_path)
        all_chunks.extend(chunks)

    print(f"Parsed into {len(all_chunks)} chunks")

    # Build embedding texts
    texts = [build_chunk_text(c) for c in all_chunks]

    # Generate embeddings
    print("Generating embeddings...")
    start = time.time()
    embeddings = generate_embeddings(texts)
    elapsed = time.time() - start
    print(f"Embedding complete in {elapsed:.1f}s")

    # Store in database
    print("Storing in database...")
    store_chunks(all_chunks, embeddings)
    print(f"Done! Stored {len(all_chunks)} chunks.")


if __name__ == "__main__":
    main()
```

**Step 2: Test with a dry run** (optional, requires API keys and DB)

```bash
cd backend && python scripts/ingest.py
```
Expected: Discovers files, parses chunks, embeds, stores. Should complete in <5 minutes for ~2000 files.

**Step 3: Commit**

```bash
git add backend/scripts/ingest.py
git commit -m "feat: add LAPACK ingestion script"
```

---

## Task 7: Build the Retrieval Service

**Files:**
- Create: `backend/app/services/retrieval.py`
- Create: `backend/tests/test_retrieval.py`

**Step 1: Write tests**

```python
# backend/tests/test_retrieval.py
from app.services.retrieval import reciprocal_rank_fusion


def test_rrf_merges_two_result_lists():
    vector_results = [
        {"id": 1, "score": 0.95},
        {"id": 2, "score": 0.85},
        {"id": 3, "score": 0.75},
    ]
    keyword_results = [
        {"id": 2, "score": 10.5},
        {"id": 4, "score": 8.2},
        {"id": 1, "score": 6.1},
    ]
    merged = reciprocal_rank_fusion(vector_results, keyword_results, k=60)
    # ID 2 appears in both lists at good ranks -> should be ranked high
    ids = [r["id"] for r in merged]
    assert ids[0] in (1, 2)  # top results should be IDs that appear in both lists
    assert len(merged) == 4  # 4 unique IDs total


def test_rrf_handles_empty_keyword_results():
    vector_results = [{"id": 1, "score": 0.9}]
    merged = reciprocal_rank_fusion(vector_results, [], k=60)
    assert len(merged) == 1
    assert merged[0]["id"] == 1
```

**Step 2: Run tests, verify they fail**

```bash
cd backend && python -m pytest tests/test_retrieval.py -v
```
Expected: FAIL -- ImportError

**Step 3: Implement retrieval service**

```python
# backend/app/services/retrieval.py
import openai
import psycopg2
from pgvector.psycopg2 import register_vector

from app.config import settings
from app.models.schemas import ChunkResult


def reciprocal_rank_fusion(
    vector_results: list[dict],
    keyword_results: list[dict],
    k: int = 60,
) -> list[dict]:
    """Merge vector and keyword results using Reciprocal Rank Fusion."""
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


def embed_query(query: str) -> list[float]:
    """Embed a search query using OpenAI."""
    client = openai.OpenAI(api_key=settings.openai_api_key)
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=query,
    )
    return response.data[0].embedding


def vector_search(embedding: list[float], top_k: int = 10, routine_type: str | None = None) -> list[dict]:
    """Search pgvector for similar chunks."""
    conn = psycopg2.connect(settings.database_url)
    register_vector(conn)
    cur = conn.cursor()

    filter_clause = ""
    params: list = [embedding, top_k]
    if routine_type:
        filter_clause = "WHERE routine_type = %s"
        params = [embedding, routine_type, top_k]

    query = f"""
        SELECT id, file_path, line_start, line_end, subroutine_name,
               routine_type, content, 1 - (embedding <=> %s::vector) AS score
        FROM code_chunks
        {filter_clause}
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """

    if routine_type:
        cur.execute(
            """
            SELECT id, file_path, line_start, line_end, subroutine_name,
                   routine_type, content, 1 - (embedding <=> %s::vector) AS score
            FROM code_chunks
            WHERE routine_type = %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (embedding, routine_type, embedding, top_k),
        )
    else:
        cur.execute(
            """
            SELECT id, file_path, line_start, line_end, subroutine_name,
                   routine_type, content, 1 - (embedding <=> %s::vector) AS score
            FROM code_chunks
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (embedding, embedding, top_k),
        )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "id": r[0],
            "file_path": r[1],
            "line_start": r[2],
            "line_end": r[3],
            "subroutine_name": r[4],
            "routine_type": r[5],
            "content": r[6],
            "score": float(r[7]),
        }
        for r in rows
    ]


def keyword_search(query: str, top_k: int = 10) -> list[dict]:
    """BM25-style search using PostgreSQL tsvector."""
    conn = psycopg2.connect(settings.database_url)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, file_path, line_start, line_end, subroutine_name,
               routine_type, content, ts_rank(fts, plainto_tsquery('english', %s)) AS score
        FROM code_chunks
        WHERE fts @@ plainto_tsquery('english', %s)
        ORDER BY score DESC
        LIMIT %s
        """,
        (query, query, top_k),
    )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "id": r[0],
            "file_path": r[1],
            "line_start": r[2],
            "line_end": r[3],
            "subroutine_name": r[4],
            "routine_type": r[5],
            "content": r[6],
            "score": float(r[7]),
        }
        for r in rows
    ]


def search(query: str, top_k: int = 5, routine_type: str | None = None) -> list[ChunkResult]:
    """Hybrid search: vector + keyword with RRF fusion."""
    query_embedding = embed_query(query)

    vector_results = vector_search(query_embedding, top_k=10, routine_type=routine_type)
    kw_results = keyword_search(query, top_k=10)

    merged = reciprocal_rank_fusion(vector_results, kw_results)

    return [
        ChunkResult(
            file_path=r["file_path"],
            line_start=r["line_start"],
            line_end=r["line_end"],
            subroutine_name=r.get("subroutine_name"),
            routine_type=r.get("routine_type"),
            content=r["content"],
            relevance_score=round(r["rrf_score"], 4),
        )
        for r in merged[:top_k]
    ]
```

**Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_retrieval.py -v
```
Expected: 2 tests PASS.

**Step 5: Commit**

```bash
git add backend/app/services/retrieval.py backend/tests/test_retrieval.py
git commit -m "feat: add hybrid retrieval service with RRF fusion"
```

---

## Task 8: Build the Answer Generation Service

**Files:**
- Create: `backend/app/services/generation.py`

**Step 1: Implement generation service**

```python
# backend/app/services/generation.py
import anthropic

from app.config import settings
from app.models.schemas import ChunkResult

SYSTEM_PROMPT = """You are a legacy code expert analyzing Fortran source code from the LAPACK library (Linear Algebra PACKage). Given code snippets retrieved from the codebase, answer the user's question.

Rules:
- Always cite specific file paths and line numbers in [file:line] format
- Explain what the code does in plain English
- Mention related routines the user might want to explore
- Be concise but thorough"""


def build_context(chunks: list[ChunkResult]) -> str:
    """Format retrieved chunks into context for the LLM."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"--- Result {i}: {chunk.file_path}:{chunk.line_start}-{chunk.line_end} "
            f"(Subroutine: {chunk.subroutine_name}, Type: {chunk.routine_type}) ---\n"
            f"{chunk.content}\n"
        )
    return "\n".join(parts)


def generate_answer(query: str, chunks: list[ChunkResult]) -> str:
    """Generate an answer using Claude Haiku with retrieved context."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    context = build_context(chunks)

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Retrieved code context:\n\n{context}\n\nQuestion: {query}",
            }
        ],
    )

    return message.content[0].text


async def stream_answer(query: str, chunks: list[ChunkResult]):
    """Stream an answer using Claude Haiku via SSE."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    context = build_context(chunks)

    with client.messages.stream(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Retrieved code context:\n\n{context}\n\nQuestion: {query}",
            }
        ],
    ) as stream:
        for text in stream.text_stream:
            yield text
```

**Step 2: Commit**

```bash
git add backend/app/services/generation.py
git commit -m "feat: add Claude answer generation service with streaming"
```

---

## Task 9: Wire Up the API Endpoint

**Files:**
- Modify: `backend/app/routers/query.py`

**Step 1: Update the query router with real implementation**

```python
# backend/app/routers/query.py
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.schemas import QueryRequest, QueryResponse, ChunkResult
from app.services.retrieval import search
from app.services.generation import generate_answer, stream_answer

router = APIRouter()


@router.post("/query")
async def query_codebase(request: QueryRequest):
    """Main query endpoint -- retrieves code and streams LLM answer."""
    chunks = search(
        query=request.query,
        top_k=request.top_k,
        routine_type=request.routine_type,
    )

    async def event_stream():
        # First send the chunks as a JSON event
        yield f"data: {json.dumps({'type': 'chunks', 'chunks': [c.model_dump() for c in chunks]})}\n\n"

        # Then stream the answer
        full_answer = ""
        async for token in stream_answer(request.query, chunks):
            full_answer += token
            yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'answer': full_answer})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/query/sync")
async def query_codebase_sync(request: QueryRequest) -> QueryResponse:
    """Non-streaming version for testing."""
    chunks = search(
        query=request.query,
        top_k=request.top_k,
        routine_type=request.routine_type,
    )
    answer = generate_answer(request.query, chunks)
    return QueryResponse(answer=answer, chunks=chunks)
```

**Step 2: Test locally** (requires API keys + ingested data)

```bash
cd backend && python -m uvicorn app.main:app --reload --port 8000
```

Test sync endpoint:
```bash
curl -X POST http://localhost:8000/api/query/sync \
  -H "Content-Type: application/json" \
  -d '{"query": "What does DGESV do?"}'
```

Expected: JSON response with `answer` and `chunks` array.

**Step 3: Commit**

```bash
git add backend/app/routers/query.py
git commit -m "feat: wire up query endpoint with streaming SSE"
```

---

## Task 10: Set Up Next.js Frontend

**Files:**
- Create: `frontend/` via `create-next-app`
- Create: `frontend/app/page.tsx`
- Create: `frontend/app/layout.tsx`
- Create: `frontend/components/QueryInput.tsx`
- Create: `frontend/components/AnswerPanel.tsx`
- Create: `frontend/components/CodeBlock.tsx`
- Create: `frontend/components/ResultsList.tsx`

**Step 1: Scaffold Next.js project**

```bash
cd /Users/xian/legacylens
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --no-src-dir --import-alias "@/*"
```

When prompted, accept defaults (Yes to all).

**Step 2: Create `frontend/.env.local`**

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Step 3: Create `frontend/components/QueryInput.tsx`**

```tsx
"use client";

import { useState } from "react";

interface QueryInputProps {
  onSubmit: (query: string) => void;
  isLoading: boolean;
}

export default function QueryInput({ onSubmit, isLoading }: QueryInputProps) {
  const [query, setQuery] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSubmit(query.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-3xl">
      <div className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask about the LAPACK codebase... (e.g., 'What does DGESV do?')"
          className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900 bg-white"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={isLoading || !query.trim()}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
        >
          {isLoading ? "Searching..." : "Search"}
        </button>
      </div>
    </form>
  );
}
```

**Step 4: Create `frontend/components/AnswerPanel.tsx`**

```tsx
"use client";

interface AnswerPanelProps {
  answer: string;
  isStreaming: boolean;
}

export default function AnswerPanel({ answer, isStreaming }: AnswerPanelProps) {
  if (!answer) return null;

  return (
    <div className="w-full max-w-3xl bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
      <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
        Answer {isStreaming && <span className="animate-pulse">...</span>}
      </h2>
      <div className="prose prose-sm max-w-none text-gray-800 whitespace-pre-wrap">
        {answer}
      </div>
    </div>
  );
}
```

**Step 5: Create `frontend/components/CodeBlock.tsx`**

```tsx
interface CodeBlockProps {
  code: string;
  filePath: string;
  lineStart: number;
  lineEnd: number;
}

export default function CodeBlock({ code, filePath, lineStart, lineEnd }: CodeBlockProps) {
  return (
    <div className="bg-gray-900 rounded-lg overflow-hidden">
      <div className="px-4 py-2 bg-gray-800 text-gray-300 text-xs font-mono flex justify-between">
        <span>{filePath}</span>
        <span>Lines {lineStart}-{lineEnd}</span>
      </div>
      <pre className="p-4 text-sm text-gray-100 overflow-x-auto">
        <code>{code}</code>
      </pre>
    </div>
  );
}
```

**Step 6: Create `frontend/components/ResultsList.tsx`**

```tsx
import CodeBlock from "./CodeBlock";

interface Chunk {
  file_path: string;
  line_start: number;
  line_end: number;
  subroutine_name: string | null;
  routine_type: string | null;
  content: string;
  relevance_score: number;
}

interface ResultsListProps {
  chunks: Chunk[];
}

export default function ResultsList({ chunks }: ResultsListProps) {
  if (chunks.length === 0) return null;

  return (
    <div className="w-full max-w-3xl space-y-4">
      <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
        Retrieved Code ({chunks.length} results)
      </h2>
      {chunks.map((chunk, i) => (
        <div key={i} className="border border-gray-200 rounded-lg overflow-hidden shadow-sm">
          <div className="px-4 py-2 bg-gray-50 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-gray-700">
                {chunk.subroutine_name || "Unknown"}
              </span>
              {chunk.routine_type && (
                <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full">
                  {chunk.routine_type}
                </span>
              )}
            </div>
            <span className="text-xs text-gray-500">
              Score: {chunk.relevance_score.toFixed(4)}
            </span>
          </div>
          <CodeBlock
            code={chunk.content}
            filePath={chunk.file_path}
            lineStart={chunk.line_start}
            lineEnd={chunk.line_end}
          />
        </div>
      ))}
    </div>
  );
}
```

**Step 7: Create `frontend/app/page.tsx`**

```tsx
"use client";

import { useState } from "react";
import QueryInput from "@/components/QueryInput";
import AnswerPanel from "@/components/AnswerPanel";
import ResultsList from "@/components/ResultsList";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Chunk {
  file_path: string;
  line_start: number;
  line_end: number;
  subroutine_name: string | null;
  routine_type: string | null;
  content: string;
  relevance_score: number;
}

export default function Home() {
  const [answer, setAnswer] = useState("");
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);

  const handleQuery = async (query: string) => {
    setIsLoading(true);
    setIsStreaming(true);
    setAnswer("");
    setChunks([]);

    try {
      const response = await fetch(`${API_URL}/api/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, top_k: 5 }),
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error("No response body");

      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data = JSON.parse(line.slice(6));

          if (data.type === "chunks") {
            setChunks(data.chunks);
            setIsLoading(false);
          } else if (data.type === "token") {
            setAnswer((prev) => prev + data.token);
          } else if (data.type === "done") {
            setIsStreaming(false);
          }
        }
      }
    } catch (error) {
      console.error("Query failed:", error);
      setAnswer("Error: Failed to query the backend. Is the server running?");
    } finally {
      setIsLoading(false);
      setIsStreaming(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-50 flex flex-col items-center px-4 py-12 gap-6">
      <div className="text-center mb-4">
        <h1 className="text-3xl font-bold text-gray-900">LegacyLens</h1>
        <p className="text-gray-500 mt-1">
          RAG-powered search for the LAPACK Fortran codebase
        </p>
      </div>

      <QueryInput onSubmit={handleQuery} isLoading={isLoading} />
      <AnswerPanel answer={answer} isStreaming={isStreaming} />
      <ResultsList chunks={chunks} />
    </main>
  );
}
```

**Step 8: Test the frontend**

```bash
cd frontend && npm run dev
```
Expected: Opens at `http://localhost:3000`, shows search bar. Queries will fail until backend is running with data.

**Step 9: Commit**

```bash
git add frontend/
git commit -m "feat: add Next.js frontend with query interface and streaming"
```

---

## Task 11: End-to-End Test (Local)

**Step 1: Ensure `.env` is configured** with all API keys and Supabase credentials.

**Step 2: Run ingestion**

```bash
cd backend && source .venv/bin/activate && python scripts/ingest.py
```
Expected: All chunks ingested.

**Step 3: Start backend**

```bash
cd backend && python -m uvicorn app.main:app --reload --port 8000
```

**Step 4: Start frontend**

```bash
cd frontend && npm run dev
```

**Step 5: Test queries in the browser at `http://localhost:3000`**

Test these queries:
1. "What does DGESV do?"
2. "Find all eigenvalue routines"
3. "What are the dependencies of DGESV?"
4. "Show me error handling patterns in LAPACK"
5. "How does LU factorization work?"

Expected: Each returns relevant code chunks and a coherent LLM answer.

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: complete MVP -- end-to-end RAG pipeline working locally"
```

---

## Task 12: Deploy

**Step 1: Deploy backend to Railway**

Create a `backend/Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Push to GitHub, connect Railway to the repo, set root directory to `backend/`, add all env vars.

**Step 2: Deploy frontend to Vercel**

```bash
cd frontend
```

Update `frontend/.env.production`:
```
NEXT_PUBLIC_API_URL=https://your-railway-url.up.railway.app
```

Push to GitHub, connect Vercel to the repo, set root directory to `frontend/`, add env vars.

**Step 3: Verify deployment**

- Backend: `curl https://your-railway-url.up.railway.app/api/health`
- Frontend: Visit Vercel URL, run a test query

**Step 4: Commit deployment configs**

```bash
git add backend/Dockerfile
git commit -m "feat: add deployment configuration for Railway"
```

---

## Summary

| Task | Description | Key Output |
|---|---|---|
| 1 | Git + project structure | Repo initialized with all planning docs |
| 2 | Python backend scaffold | FastAPI running with health endpoint |
| 3 | Database schema | pgvector table + indexes on Supabase |
| 4 | Download LAPACK | ~2200 Fortran files in `data/lapack/` |
| 5 | Fortran parser + ingestion service | Chunking by subroutine boundaries with metadata |
| 6 | Ingestion script | One-time script to populate the database |
| 7 | Retrieval service | Hybrid vector + BM25 search with RRF fusion |
| 8 | Generation service | Claude Haiku streaming answers |
| 9 | API endpoint | POST /api/query with SSE streaming |
| 10 | Next.js frontend | Query interface with streaming answers |
| 11 | End-to-end test | Full pipeline working locally |
| 12 | Deploy | Public URL on Railway + Vercel |
