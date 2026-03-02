# LegacyLens Pre-Search Document

## Phase 1: Define Your Constraints

---

### 1. Scale & Load Profile

**Target codebase:** LAPACK (scoped subset) -- double-precision routines from `SRC/` (~500 files) + `BLAS/SRC/` (~170 files) = ~670 Fortran files, ~100,000+ LOC of authentic legacy Fortran 77/90 code.

**Expected query volume:** Low -- demo/evaluation context. ~10-50 queries/day during development, up to ~100/day during review and grading.

**Ingestion model:** Batch ingestion (one-time indexing of the full codebase at startup). No incremental updates needed -- legacy codebases are static by nature.

**Latency requirements:** <3 seconds end-to-end per query (per project spec). Target <2 seconds for retrieval, <1 second for LLM response streaming start.

---

### 2. Budget & Cost Ceiling

| Cost Category | Estimate |
|---|---|
| Vector database hosting | $0 (Supabase free tier or Qdrant free tier) |
| Embedding API costs | ~$0.50-2.00 total for full indexing (100K LOC at ~$0.02-0.18/1M tokens) |
| LLM API costs (dev + testing) | ~$5-15 total (Claude Haiku for most queries, Sonnet for complex ones) |
| Deployment hosting | $0-5/month (Vercel free tier for frontend, Railway/Render free tier for backend) |
| **Total development budget** | **~$10-25** |

**Where to trade money for time:** Use managed services (Supabase, Vercel) over self-hosting to save setup time. Use API-based embeddings (Voyage or OpenAI) over local models to avoid GPU infrastructure.

---

### 3. Time to Ship

**MVP timeline:** 24 hours (Tuesday deadline per spec).

**Must-have features (MVP):**
- Ingest at least one legacy codebase
- Syntax-aware chunking
- Generate and store embeddings in a vector database
- Semantic search with natural language queries
- Return code snippets with file/line references
- Basic LLM answer generation
- Deployed and publicly accessible

**Nice-to-have features (Final submission):**
- Code explanation, dependency mapping, pattern detection, documentation generation (4+ of 8 code understanding features)
- Re-ranking for improved precision
- Hybrid search (vector + keyword)
- Confidence/relevance scores

**Framework learning curve acceptable?** Yes -- LlamaIndex has focused documentation and the CodeSplitter/vector store integration is well-documented. Estimated 2-4 hours to get productive.

---

### 4. Data Sensitivity

**Codebase is open source:** Yes. LAPACK is BSD-licensed. No restrictions on sending code to external APIs.

**Can you send code to external APIs?** Yes -- no proprietary or sensitive data. All code is publicly available on GitHub/Netlib.

**Data residency requirements:** None. US-based cloud services are acceptable.

---

### 5. Team & Skill Constraints

**Familiarity with vector databases:** Moderate -- experience with SQL databases (PostgreSQL), some exposure to vector similarity concepts. pgvector leverages existing SQL knowledge.

**Experience with RAG frameworks:** Beginner-to-intermediate with LlamaIndex/LangChain. LlamaIndex's focused API surface is preferable to LangChain's broader but more complex one.

**Comfort with the target legacy language:** Fortran -- basic reading comprehension (subroutines, COMMON blocks, array operations, fixed-format column rules).

---

## Phase 2: Architecture Discovery

---

### 6. Vector Database Selection

#### Comparison of Top Candidates

| Feature | Pinecone | Qdrant | ChromaDB | pgvector (Supabase) |
|---|---|---|---|---|
| **Free tier** | 2 GB cloud (pauses after 3 weeks idle) | 1 GB cloud forever (suspends after 1 week idle) | OSS + $100 cloud credits | 500 MB Supabase (no idle suspension) |
| **Setup time** | ~10 min | ~10 min | ~5 min | ~15 min |
| **Hybrid search** | Yes (dense+sparse, you provide sparse vectors) | Yes (Query API, server-side) | Yes (RRF fusion) | Manual (SQL tsvector + pgvector + RRF) |
| **Metadata filtering** | Strong (schema-based) | Best-in-class (filterable HNSW) | Basic (where clauses) | Best (full SQL WHERE/JOIN) |
| **Public deployment** | Built-in API endpoint | Free cloud tier API | Needs separate hosting | Supabase provides REST API |
| **DX simplicity** | 9/10 | 8/10 | 10/10 | 7/10 |
| **Open source** | No | Yes (Apache 2.0) | Yes (Apache 2.0) | Yes |

#### Pros/Cons Deep Dive

**Pinecone**
- Pros: Zero-ops, fastest to working demo, great SDK, native hybrid search
- Cons: Vendor lock-in, closed source, free tier pauses after 3 weeks (demo goes cold), no self-hosting

**Qdrant**
- Pros: 1 GB free forever, Rust performance, filterable HNSW ideal for code metadata, clean API
- Cons: Free tier suspends after 1 week idle (needs keep-alive ping), smaller ecosystem

**ChromaDB**
- Pros: Fastest prototype (5 min), built-in embeddings, LangChain default, $100 cloud credits
- Cons: Embedded mode not publicly accessible, basic metadata filtering, less production-hardened

**pgvector via Supabase**
- Pros: Full SQL power for metadata (file paths, function names, line numbers), no idle suspension, complete backend (auth, REST API, storage) included free, vectors + metadata + app data in one place
- Cons: Hybrid search requires manual SQL orchestration, not a purpose-built vector DB, missing built-in reranking/MMR

#### Decision: **pgvector via Supabase**

**Rationale:** For a legacy codebase RAG system, metadata filtering is critical -- queries about specific file types, function names, and Fortran subroutine categories all require rich metadata queries. SQL gives the most flexible filtering. Supabase's free tier includes the full backend stack (no idle suspension, REST API, auth) which means one service instead of three. The hybrid search (tsvector + pgvector + RRF) handles both exact identifier matching ("DGESV", "DGEMM") and semantic similarity, which is essential for legacy code where exact symbol names matter alongside conceptual queries.

---

### 7. Embedding Strategy

#### Comparison

| Model | Price/1M tokens | Dims | Context | Code-Specific? | Code Retrieval Score |
|---|---|---|---|---|---|
| OpenAI text-embedding-3-small | $0.02 ($0.01 batch) | 1536 | 8K | No | ~77% (baseline) |
| OpenAI text-embedding-3-large | $0.13 ($0.065 batch) | 3072 | 8K | No | ~78% |
| Voyage code-3 | $0.18 ($0.12 batch) | 1024 | 32K | **Yes** | **~92%** |
| Cohere embed-english-v3 | $0.10 | 1024 | 512 | No | N/A |
| sentence-transformers (local) | $0 | 384 | 256 | No | ~56% |

#### Pros/Cons Deep Dive

**Voyage code-3**
- Pros: Best code retrieval by 14% over nearest competitor, 32K context handles full Fortran subroutines, Matryoshka support (reduce to 256 dims), 200M free tokens
- Cons: Most expensive per-token ($0.18), newer model with less community tooling, acquired by MongoDB (pricing may change)

**OpenAI text-embedding-3-small**
- Pros: Cheapest API option ($0.02/1M), batch API halves cost, generous rate limits, Matryoshka support
- Cons: Not code-trained (14% worse on code retrieval), 8K context may truncate long programs

**Cohere embed-english-v3**
- Cons: **512-token context limit is disqualifying** for Fortran code where single subroutines exceed this

**sentence-transformers (local)**
- Cons: **256-token context limit is disqualifying**, worst quality by large margin

#### Decision: **OpenAI text-embedding-3-small** (primary) with potential upgrade to **Voyage code-3** if budget allows

**Rationale:** For MVP within 24 hours, OpenAI text-embedding-3-small is the pragmatic choice: dirt cheap ($0.02/1M tokens), excellent SDK, generous rate limits, and 8K context is sufficient when combined with good chunking (individual Fortran subroutines typically fit within 8K). The 14% quality gap vs Voyage code-3 can be partially compensated by hybrid search (BM25 catches exact identifiers that embedding models miss). For the final submission, upgrading to Voyage code-3 would improve retrieval precision noticeably, and the 200M free token tier covers the full indexing cost.

---

### 8. Chunking Approach

**Strategy: Syntax-aware splitting (primary) + fixed-size with overlap (fallback)**

**For Fortran (LAPACK/BLAS):**
- Chunk by **SUBROUTINE/FUNCTION** boundary -- LAPACK's one-subroutine-per-file structure makes this natural
- Include the **comment header block** (Purpose, Parameters, Algorithm description) as part of each chunk -- this is critical since LAPACK has 10:1 documentation-to-code ratio
- Prepend metadata as text prefix: `"File: dgesv.f | Subroutine: DGESV | Type: Driver | Precision: Double"`

**Optimal chunk size:** 500-1500 tokens (fits well within OpenAI's 8K context and Voyage's 32K). Most LAPACK subroutines naturally fall in this range.

**Overlap strategy:** 100-200 token overlap between consecutive chunks within the same file to preserve context at boundaries. Not needed for most LAPACK files (one subroutine per file) but useful for larger files that contain multiple internal routines.

**Metadata to preserve per chunk:**
- File path
- Line number range (start:end)
- Language (Fortran)
- Subroutine/function name
- Routine type (driver, computational, auxiliary)
- Precision (single/double/complex/double-complex)
- Dependencies (CALL targets)

---

### 9. Retrieval Pipeline

**Top-k value:** k=10 for initial retrieval, then re-rank to top-5 for context assembly. The 10->5 two-stage approach balances recall (casting a wide net) with precision (presenting only relevant results).

**Re-ranking approach:** Cohere Rerank API or cross-encoder reranking. If budget-constrained, use simple relevance score thresholding (discard chunks below a cosine similarity threshold of 0.3).

**Context window management:**
- Assemble top-5 chunks into a single context block
- Include surrounding context: for each retrieved chunk, also include 1 chunk before and 1 chunk after from the same file (sliding window)
- Total context budget: ~4,000 tokens for retrieved code + ~500 tokens for system prompt + ~500 tokens for user query = ~5,000 tokens per request

**Multi-query or query expansion:** For MVP, single query. For final submission, implement query expansion: the LLM rephrases the user's natural language query into 2-3 variants (e.g., "solve linear system" -> ["DGESV linear equation solver", "LU factorization solve", "matrix system of equations"]), retrieve for each, then merge and deduplicate results.

---

### 10. Answer Generation

**LLM for synthesis:** Claude Haiku 4.5 (primary -- $1/$5 per 1M tokens, fast, good code understanding) with Claude Sonnet 4.6 ($3/$15 per 1M tokens) for complex architectural queries.

**Prompt template design:**
```
You are a legacy code expert analyzing {language} source code.
Given the following code snippets retrieved from the {project} codebase,
answer the user's question. Always cite specific file paths and line numbers.

Retrieved code context:
{retrieved_chunks}

User question: {query}

Provide a clear, concise answer with:
1. Direct answer to the question
2. Relevant code snippets with file:line references
3. Explanation of how the code works
4. Related functions/modules the user might want to explore
```

**Citation/reference formatting:** Each answer includes `[file_path:line_start-line_end]` references that link to the source code. Display retrieved chunks with syntax highlighting.

**Streaming vs batch:** Streaming response for the web interface (better UX -- user sees the answer forming). Batch for CLI mode.

---

### 11. Framework Selection

#### Comparison

| Dimension | LangChain | LlamaIndex | Haystack | Custom |
|---|---|---|---|---|
| **Code chunking** | Regex-based per-language | AST-based (tree-sitter) | Basic splitter only | Full control |
| **Learning curve** | Medium-High | Medium | Medium-High | High |
| **Vector store integrations** | 50+ | 20+ | 10+ | Direct SDK |
| **Community** | ~100K stars | ~40K stars | ~18K stars | N/A |
| **Framework overhead** | ~10ms | ~6ms | ~5.9ms | Near-zero |
| **Retrieval quality** | Good | Best (35% improvement in 2025) | Good | Depends on implementation |

**LangChain**
- Pros: Largest ecosystem, most tutorials, LangSmith observability, broadest integrations
- Cons: Frequent API breaking changes, heavy abstraction hides behavior, regex-based code splitting (not AST), unnecessary complexity for focused RAG

**LlamaIndex**
- Pros: AST-based CodeSplitter (tree-sitter), best retrieval benchmarks, hierarchical indexing, purpose-built for RAG, lower overhead
- Cons: Narrower than LangChain (less suited for multi-agent), smaller community, deployment requires manual FastAPI wrapper

**Haystack**
- Pros: Most production-ready architecture, lowest overhead, explicit typed pipelines, built-in evaluation
- Cons: No dedicated code splitter (needs custom), smallest community, steepest learning curve

**Custom**
- Pros: Zero framework overhead, maximum control, smallest dependency footprint
- Cons: Build everything from scratch, no community support, reinventing wheels

#### Decision: **LlamaIndex**

**Rationale:** The AST-based CodeSplitter using tree-sitter is the decisive advantage. For legacy Fortran code, it can parse along subroutine/function boundaries rather than arbitrary character counts. The 35% retrieval accuracy improvement over alternatives and hierarchical indexing (file -> section -> function) directly maps to navigating legacy codebases. LlamaIndex's focused RAG API surface means less time fighting framework abstractions and more time on the actual pipeline. The pgvector integration is well-documented.

---

## Phase 3: Post-Stack Refinement

---

### 12. Failure Mode Analysis

**When retrieval finds nothing relevant:**
- Return a "low confidence" indicator when the highest similarity score is below threshold (0.3)
- Suggest alternative phrasings or related terms
- Fall back to keyword search (BM25) which may catch exact identifiers the embedding model missed
- Display: "No highly relevant code found. Here are the closest matches (low confidence):"

**How to handle ambiguous queries:**
- Use the LLM to disambiguate: "Did you mean X (function name) or Y (concept)?"
- For very short queries (1-2 words), expand them using the LLM before retrieval
- Show top results from multiple interpretation paths

**Rate limiting and error handling:**
- Implement client-side rate limiting (max 10 queries/minute per user)
- Cache embedding vectors for repeated queries
- Graceful degradation: if the LLM API is down, still return raw retrieval results without synthesis
- Retry with exponential backoff for transient API errors (max 3 retries)

---

### 13. Evaluation Strategy

**Measuring retrieval precision:**
- Create a ground truth dataset of 20-30 query-answer pairs manually
- For each query, annotate which files/functions should be retrieved
- Measure Precision@5, Recall@5, and MRR (Mean Reciprocal Rank)
- Target: >70% relevant chunks in top-5 results (per project spec)

**Ground truth dataset:** Hand-curated from the LAPACK codebase:
- "What does DGESV do?" -> Expected: `SRC/dgesv.f`
- "Find all eigenvalue routines" -> Expected: `SRC/dsyev.f`, `SRC/dgeev.f`, etc.
- "Show error handling for singular matrices" -> Expected: INFO parameter checks in driver routines
- "What routines call DGEMM?" -> Expected: driver and computational routines that use matrix multiply
- "How does LU factorization work?" -> Expected: `SRC/dgetrf.f`, `SRC/dgetf2.f`

**User feedback collection:** Thumbs up/down on each answer in the web interface. Log query + retrieved chunks + user rating for iterative improvement.

---

### 14. Performance Optimization

**Caching strategy:**
- Cache embedding vectors for queries (LRU cache, top 100 recent queries)
- Cache LLM responses for identical query + context combinations (TTL: 1 hour)
- Pre-compute and store file-level summaries during ingestion (no runtime LLM call needed for "what does this file do?" queries)

**Index optimization:**
- Use HNSW index in pgvector for approximate nearest neighbor search (faster than exact search)
- Create GIN indexes on metadata columns (language, file_path, function_name) for filtered queries
- Partition vectors by routine type (driver, computational, auxiliary, BLAS) to narrow search space

**Query preprocessing:**
- Normalize query text (lowercase, strip punctuation)
- Extract code identifiers (anything in UPPERCASE or camelCase) and boost their weight in hybrid search
- For Fortran: map common modern terms to legacy equivalents ("function" -> "SUBROUTINE", "method" -> "SUBROUTINE", "array multiply" -> "DGEMM")

---

### 15. Observability

**Logging for debugging retrieval issues:**
- Log every query with: timestamp, raw query, processed query, embedding vector (hash), top-k results with scores, final answer (truncated), latency breakdown (embedding time, search time, LLM time)
- Structured JSON logging to stdout (captured by deployment platform)

**Metrics to track:**
- Query latency (p50, p95, p99) -- target p95 < 3s
- Retrieval precision (from user feedback thumbs up/down)
- Embedding API latency and error rate
- LLM API latency and error rate
- Queries per day, unique users
- Most common query patterns (for improving prompt templates)

**Alerting needs:** Minimal for a demo project. Monitor deployment platform health dashboard (Vercel/Railway). Set up Supabase email alerts for database usage approaching free tier limits.

---

### 16. Deployment & DevOps

**CI/CD for index updates:** Not needed for MVP (one-time batch ingestion). For final submission, a simple script that re-indexes on `git push` to main (triggered via GitHub Actions).

**Environment management:**
- Development: Local (ChromaDB embedded or local pgvector for fast iteration)
- Production: Supabase (pgvector) + Vercel (frontend) + Railway or Render (backend API)
- Environment variables managed via platform-specific secrets (Vercel env vars, Railway secrets)

**Secrets handling for API keys:**
- Never commit API keys to git
- Use `.env.local` for development (in `.gitignore`)
- Use platform environment variables for production (Supabase, Vercel, Railway all support this)
- Required secrets: `OPENAI_API_KEY` (embeddings), `ANTHROPIC_API_KEY` (LLM), `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`

---

## Target Codebase Decision

### Decision: **LAPACK** (Fortran)

#### Why LAPACK?

| Strength | Detail |
|---|---|
| **Authentic legacy Fortran** | Real Fortran 77/90 code, not a compiler written in C |
| **Exceptional documentation** | 10:1 documentation-to-code ratio in every file |
| **Perfect natural chunking** | One subroutine per file, no ambiguity |
| **Rich query potential** | Deep call chains, naming conventions, algorithm families |
| **Real-world significance** | Used by NumPy, MATLAB, R -- everyone knows LAPACK |
| **Clean structure** | ~670 files (scoped to double-precision + BLAS), ~100K LOC |
| **Meets all requirements** | 100K+ LOC across 670+ files, well above the 10K/50 minimums |

#### Adapted Test Scenarios for LAPACK

The project spec lists COBOL-style test queries. Here is how they map to LAPACK:

| Spec Query | LAPACK Equivalent |
|---|---|
| "Where is the main entry point?" | "What are the top-level driver routines?" (DGESV, DSYEV, etc.) |
| "What functions modify CUSTOMER-RECORD?" | "What routines modify the matrix A in-place?" |
| "Explain what CALCULATE-INTEREST does" | "Explain what DGESV does" |
| "Find all file I/O operations" | "Find all routines that handle workspace allocation" |
| "What are the dependencies of MODULE-X?" | "What are the dependencies of DGESV?" (DGETRF -> DGETRS) |
| "Show me error handling patterns" | "Show me INFO parameter error checking patterns" |

#### Why Not the Other Options?

| Project | Rejection Reason |
|---|---|
| **GnuCOBOL** | Written in C/Yacc -- it's a compiler *for* COBOL, not a COBOL codebase |
| **gfortran (GCC)** | Written in C++ -- it's a compiler *for* Fortran, not Fortran code. Also massive/complex to extract from GCC |
| **BLAS standalone** | Too small (~170 files, ~15-25K LOC) and too repetitive (4 precision variants of each routine) |
| **OpenCOBOL Contrib** | Same problem as GnuCOBOL -- 99.6% C/Shell, only 0.4% COBOL |

---

## Final Technology Stack Summary

| Layer | Technology | Rationale |
|---|---|---|
| **Target Codebase** | LAPACK (Fortran) | Authentic legacy Fortran, 10:1 doc ratio, one-subroutine-per-file, 670+ files |
| **Vector Database** | pgvector via Supabase | Full SQL metadata filtering, no idle suspension, complete free backend |
| **Embedding Model** | OpenAI text-embedding-3-small (MVP) / Voyage code-3 (upgrade) | Cost-effective for MVP, upgrade path for better code retrieval |
| **LLM** | Claude Haiku 4.5 (primary) / Sonnet 4.6 (complex queries) | Best code understanding, 200K context, cost-effective |
| **RAG Framework** | LlamaIndex | AST-based CodeSplitter, best retrieval quality, purpose-built for RAG |
| **Backend** | Python / FastAPI | LlamaIndex is Python-native, FastAPI is lightweight and async |
| **Frontend** | Next.js on Vercel | Free hosting, fast deployment, good DX |
| **Deployment** | Vercel (frontend) + Railway (backend) + Supabase (DB) | All have free tiers, publicly accessible |

### Estimated Costs

| Scale | Monthly Cost |
|---|---|
| 100 users (5 queries/user/day) | ~$8/month (LLM: $5, Embeddings: $1, Hosting: $0-2) |
| 1,000 users | ~$55/month (LLM: $45, Embeddings: $5, Hosting: $5) |
| 10,000 users | ~$500/month (LLM: $400, Embeddings: $50, Hosting: $50) |
| 100,000 users | ~$5,000/month (LLM: $4,000, Embeddings: $500, Hosting: $500) |

*Assumptions: 5 queries/user/day, ~2K tokens per query (input+output), embedding cache hit rate of 80% at scale.*
