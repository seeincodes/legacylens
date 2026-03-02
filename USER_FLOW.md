# LegacyLens - User Flow

## Primary Flow: Natural Language Code Query

```
┌─────────────────────────────────────────────────────────────┐
│                        USER                                  │
│  Opens LegacyLens web app (publicly accessible URL)         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  1. QUERY INPUT                                              │
│  User types natural language question:                       │
│  "How does LAPACK solve a system of linear equations?"       │
│                                                              │
│  Optional: Select filters (routine type, precision)          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  2. QUERY PROCESSING (Backend)                               │
│  ┌─────────────────────────────────┐                        │
│  │ Normalize query text             │                        │
│  │ Extract code identifiers (CAPS)  │                        │
│  │ Generate embedding (OpenAI)      │  ~200ms               │
│  └─────────────────┬───────────────┘                        │
│                    ▼                                         │
│  ┌─────────────────────────────────┐                        │
│  │ Vector similarity search (k=10) │                        │
│  │ + BM25 keyword search           │  ~300ms               │
│  │ + RRF fusion + re-rank to top-5 │                        │
│  └─────────────────┬───────────────┘                        │
│                    ▼                                         │
│  ┌─────────────────────────────────┐                        │
│  │ Assemble context from top-5     │                        │
│  │ chunks + surrounding code       │  ~50ms                │
│  └─────────────────┬───────────────┘                        │
│                    ▼                                         │
│  ┌─────────────────────────────────┐                        │
│  │ Send to Claude Haiku 4.5        │                        │
│  │ with prompt template + context  │  ~1-2s (streaming)    │
│  └─────────────────┬───────────────┘                        │
└─────────────────────┼───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  3. RESULTS DISPLAY                                          │
│                                                              │
│  ┌─── LLM Answer (streaming) ──────────────────────────┐    │
│  │ LAPACK solves linear systems via LU factorization.   │    │
│  │ The driver routine DGESV calls:                      │    │
│  │ 1. DGETRF - computes LU factorization [dgetrf.f:1]  │    │
│  │ 2. DGETRS - solves using the factors [dgetrs.f:1]   │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─── Retrieved Code Snippets ─────────────────────────┐    │
│  │ 📄 SRC/dgesv.f:1-177  (relevance: 0.94)            │    │
│  │ ┌─────────────────────────────────────────────┐      │    │
│  │ │  SUBROUTINE DGESV( N, NRHS, A, LDA, ...)   │      │    │
│  │ │  *  Purpose: Computes the solution to a     │      │    │
│  │ │  *  real system of linear equations A*X = B │      │    │
│  │ └─────────────────────────────────────────────┘      │    │
│  │                                                       │    │
│  │ 📄 SRC/dgetrf.f:1-215  (relevance: 0.87)            │    │
│  │ ┌─────────────────────────────────────────────┐      │    │
│  │ │  SUBROUTINE DGETRF( M, N, A, LDA, ...)     │      │    │
│  │ │  *  Purpose: Computes an LU factorization   │      │    │
│  │ │  *  of a general M-by-N matrix A            │      │    │
│  │ └─────────────────────────────────────────────┘      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  [👍 Helpful]  [👎 Not Helpful]                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  4. DRILL DOWN (Optional)                                    │
│  User clicks file reference -> sees full file with           │
│  highlighted relevant section                                │
└─────────────────────────────────────────────────────────────┘
```

## API Endpoints

```
POST /api/query
  Body: { "query": "string", "filters": { "routine_type": "driver" } }
  Response: {
    "answer": "streaming text...",
    "chunks": [
      {
        "file_path": "SRC/dgesv.f",
        "line_start": 1,
        "line_end": 177,
        "subroutine_name": "DGESV",
        "relevance_score": 0.94,
        "content": "SUBROUTINE DGESV..."
      }
    ]
  }

GET /api/file/{path}
  Response: { "content": "full file content", "language": "fortran" }

GET /api/health
  Response: { "status": "ok", "chunks_indexed": 670, "db_connected": true }
```

## Example Queries and Expected Results

| Query | Expected Top Result | Expected Answer Summary |
|---|---|---|
| "What does DGESV do?" | `SRC/dgesv.f` | Solves general system of linear equations A*X=B via LU factorization |
| "Find all eigenvalue routines" | `SRC/dsyev.f`, `SRC/dgeev.f` | Lists symmetric/general eigenvalue drivers |
| "What are the dependencies of DGESV?" | `SRC/dgesv.f` -> `dgetrf.f`, `dgetrs.f` | Call chain: DGESV -> DGETRF (factor) -> DGETRS (solve) |
| "Show me error handling patterns" | Multiple driver routines | INFO parameter checking: INFO < 0 = bad argument, INFO > 0 = singular matrix |
| "What routines call DGEMM?" | Multiple computational routines | Lists routines using the matrix-multiply workhorse |
| "Explain the LAPACK naming convention" | Multiple files | X(precision) + YY(matrix type) + ZZZ(operation) |
