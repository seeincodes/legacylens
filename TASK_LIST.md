# LegacyLens - Task List

## Phase 1: MVP (24 Hours - Tuesday Deadline)

### 1. Project Setup

- [x] Initialize git repo and project structure
- [x] Set up Python backend (FastAPI)
- [x] Set up Next.js frontend
- [x] Create Supabase project and enable pgvector extension
- [x] Configure environment variables and secrets
- [x] Create database schema (code_chunks table, indexes)

### 2. Codebase Ingestion

- [x] Download LAPACK source (double-precision SRC/ + BLAS/SRC/)
- [x] Build file discovery: recursively scan for `.f` and `.f90` files
- [x] Implement Fortran preprocessor (handle encoding, normalize whitespace, extract comments)
- [x] Implement syntax-aware chunking (subroutine/function boundaries)
- [x] Extract metadata per chunk (file path, line numbers, subroutine name, routine type, precision)
- [x] Prepend metadata as text prefix to each chunk

### 3. Embedding & Storage

- [x] Set up OpenAI embedding API integration
- [x] Batch-generate embeddings for all chunks
- [x] Insert chunks + embeddings + metadata into Supabase/pgvector
- [x] Verify storage (query count, spot-check a few known routines)
- [x] Build HNSW and full-text search indexes

### 4. Retrieval Pipeline

- [x] Implement query embedding (same model as ingestion)
- [x] Implement vector similarity search (top-k=10)
- [x] Implement basic relevance scoring and top-5 selection
- [x] Return results with file paths and line numbers
- [x] Test with sample queries ("What does DGESV do?", "Find eigenvalue routines")

### 5. Answer Generation

- [x] Set up Claude API integration (Haiku 4.5)
- [x] Build prompt template with retrieved context
- [x] Implement streaming response
- [x] Format answers with code citations [file:line]
- [x] Test end-to-end: query -> retrieve -> generate

### 6. Web Interface (MVP)

- [x] Build query input component (natural language text box)
- [x] Build results display (code snippets with syntax highlighting)
- [x] Show file paths and line numbers for each result
- [x] Display LLM-generated answer
- [x] Connect frontend to backend API

### 7. Deployment (MVP)

- [x] Deploy backend to Railway/Render
- [x] Deploy frontend to Vercel
- [x] Verify public accessibility
- [x] Test full pipeline end-to-end on deployed version
- [x] Smoke test with 5-10 representative queries

---

## Phase 2: Final Polish (Wednesday - G4 Deadline)

### 8. Code Understanding Features (pick 4+)

- [x] Code Explanation: explain subroutine purpose in plain English
- [x] Dependency Mapping: trace call chains (DGESV -> DGETRF -> DGETRS)
- [x] Pattern Detection: find similar routines across the codebase
- [x] Documentation Generation: generate docs for undocumented sections
- [x] Build frontend UI for code understanding features (action buttons on result cards + inline UnderstandPanel)

### 9. Search Improvements

- [x] Implement hybrid search (vector + BM25/tsvector with RRF fusion)
- [x] Add confidence/relevance scores to results
- [x] Implement query expansion (LLM rephrases to multiple variants)
- [x] Add metadata filters in UI (filter by routine type, precision)

### 10. UI Polish

- [x] Add syntax highlighting for Fortran code
- [x] Add "drill down" to view full file context
- [x] Add loading states and error handling
- [x] Responsive design

### 11. Documentation & Submission

- [x] Write RAG Architecture Document (1-2 pages)
- [x] Complete AI Cost Analysis (dev spend + projections)
- [ ] Record demo video (3-5 min)
- [x] Update GitHub README (setup guide, architecture overview, deployed link)
- [ ] Social post (X or LinkedIn)

---

## Phase 3: Final Submission (Sunday - GFA Deadline)

### 12. Evaluation & Metrics

- [ ] Build ground truth dataset (20-30 query-answer pairs)
- [ ] Measure Precision@5, Recall@5, MRR
- [ ] Document failure modes and edge cases
- [ ] Log actual latency metrics (p50, p95)

### 13. Performance & Reliability

- [ ] Add query caching (LRU for embeddings, TTL for LLM responses)
- [ ] Add structured logging (query, results, latency breakdown)
- [ ] Test edge cases (empty queries, very long queries, nonsense input)
- [ ] Ensure graceful degradation if APIs are down
