# LegacyLens - Task List

## Phase 1: MVP (24 Hours - Tuesday Deadline)

### 1. Project Setup
- [ ] Initialize git repo and project structure
- [ ] Set up Python backend (FastAPI + LlamaIndex)
- [ ] Set up Next.js frontend
- [ ] Create Supabase project and enable pgvector extension
- [ ] Configure environment variables and secrets
- [ ] Create database schema (code_chunks table, indexes)

### 2. Codebase Ingestion
- [ ] Download LAPACK source (double-precision SRC/ + BLAS/SRC/)
- [ ] Build file discovery: recursively scan for `.f` and `.f90` files
- [ ] Implement Fortran preprocessor (handle encoding, normalize whitespace, extract comments)
- [ ] Implement syntax-aware chunking (subroutine/function boundaries)
- [ ] Extract metadata per chunk (file path, line numbers, subroutine name, routine type, precision)
- [ ] Prepend metadata as text prefix to each chunk

### 3. Embedding & Storage
- [ ] Set up OpenAI embedding API integration
- [ ] Batch-generate embeddings for all chunks
- [ ] Insert chunks + embeddings + metadata into Supabase/pgvector
- [ ] Verify storage (query count, spot-check a few known routines)
- [ ] Build HNSW and full-text search indexes

### 4. Retrieval Pipeline
- [ ] Implement query embedding (same model as ingestion)
- [ ] Implement vector similarity search (top-k=10)
- [ ] Implement basic relevance scoring and top-5 selection
- [ ] Return results with file paths and line numbers
- [ ] Test with sample queries ("What does DGESV do?", "Find eigenvalue routines")

### 5. Answer Generation
- [ ] Set up Claude API integration (Haiku 4.5)
- [ ] Build prompt template with retrieved context
- [ ] Implement streaming response
- [ ] Format answers with code citations [file:line]
- [ ] Test end-to-end: query -> retrieve -> generate

### 6. Web Interface (MVP)
- [ ] Build query input component (natural language text box)
- [ ] Build results display (code snippets with syntax highlighting)
- [ ] Show file paths and line numbers for each result
- [ ] Display LLM-generated answer
- [ ] Connect frontend to backend API

### 7. Deployment (MVP)
- [ ] Deploy backend to Railway/Render
- [ ] Deploy frontend to Vercel
- [ ] Verify public accessibility
- [ ] Test full pipeline end-to-end on deployed version
- [ ] Smoke test with 5-10 representative queries

---

## Phase 2: Final Polish (Wednesday - G4 Deadline)

### 8. Code Understanding Features (pick 4+)
- [ ] Code Explanation: explain subroutine purpose in plain English
- [ ] Dependency Mapping: trace call chains (DGESV -> DGETRF -> DGETRS)
- [ ] Pattern Detection: find similar routines across the codebase
- [ ] Documentation Generation: generate docs for undocumented sections

### 9. Search Improvements
- [ ] Implement hybrid search (vector + BM25/tsvector with RRF fusion)
- [ ] Add confidence/relevance scores to results
- [ ] Implement query expansion (LLM rephrases to multiple variants)
- [ ] Add metadata filters in UI (filter by routine type, precision)

### 10. UI Polish
- [ ] Add syntax highlighting for Fortran code
- [ ] Add "drill down" to view full file context
- [ ] Add loading states and error handling
- [ ] Responsive design

### 11. Documentation & Submission
- [ ] Write RAG Architecture Document (1-2 pages)
- [ ] Complete AI Cost Analysis (dev spend + projections)
- [ ] Record demo video (3-5 min)
- [ ] Update GitHub README (setup guide, architecture overview, deployed link)
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

### 14. Interview Preparation
- [ ] Prepare to discuss vector database selection rationale
- [ ] Prepare to discuss chunking strategy tradeoffs
- [ ] Prepare to discuss embedding model choice
- [ ] Prepare to discuss retrieval failure handling
- [ ] Prepare behavioral questions (ambiguity, pivoting, pressure)
