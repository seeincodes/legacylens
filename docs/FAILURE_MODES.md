# LegacyLens — Failure Modes & Edge Cases

## Retrieval Failures

### 1. Auxiliary routine queries
**Problem:** Queries about low-level auxiliary routines (e.g., `DLASSQ`, `DLASET`) may return poor results because these routines have generic names and minimal documentation in their source comments.
**Impact:** Low recall for auxiliary routine lookups.
**Mitigation:** Query expansion helps by generating alternative phrasings. Adding routine-level documentation as metadata would improve recall.

### 2. Cross-precision queries
**Problem:** Asking "What does SGESV do?" when only double-precision (`D*`) variants are strongly represented in the index. The system may return `DGESV` instead, which is functionally equivalent but not the exact routine requested.
**Impact:** Technically correct answers, but subroutine name mismatch.
**Mitigation:** All precision variants are indexed; the metadata filter allows users to narrow by precision type.

### 3. Concept queries with no single routine
**Problem:** Broad conceptual queries like "How does LAPACK handle numerical stability?" don't map to a specific routine. The retriever returns somewhat relevant chunks, but no single result is a definitive answer.
**Impact:** Lower precision; scattered results.
**Mitigation:** LLM answer generation synthesizes across multiple chunks, partially compensating.

### 4. Routine name typos
**Problem:** Queries with misspelled routine names (e.g., "DGESB" instead of "DGESV") fail keyword search entirely and rely solely on vector similarity, which may or may not recover.
**Impact:** Missed exact matches; vector search may find the right routine by context.
**Mitigation:** Could add fuzzy matching or edit-distance lookup on subroutine names.

## Generation Failures

### 5. Hallucinated line numbers
**Problem:** The LLM occasionally cites line numbers that don't match the retrieved chunks, particularly when paraphrasing or combining information from multiple chunks.
**Impact:** Misleading citations that don't match source.
**Mitigation:** The system provides actual line numbers in the UI; LLM citations are supplementary.

### 6. Overly verbose answers for simple lookups
**Problem:** Asking "What is DAXPY?" returns a detailed explanation when a one-line answer would suffice. The LLM tends toward thoroughness.
**Impact:** User experience; not a correctness issue.
**Mitigation:** Could add a "brief mode" system prompt variant.

## Chunking Failures

### 7. Large subroutines exceed embedding context
**Problem:** Some LAPACK routines (e.g., `DGEEV`, `DLASQ1`) are hundreds of lines. The full chunk is truncated at 15K characters before embedding, potentially losing the END section.
**Impact:** Incomplete representation in vector space; tail content not searchable.
**Mitigation:** Sub-function chunking with overlap would preserve full content.

### 8. Non-subroutine code missed
**Problem:** Helper blocks, DATA statements, and module-level code that don't match the `SUBROUTINE`/`FUNCTION` regex are captured as whole-file fallback chunks with the filename as the subroutine name.
**Impact:** These chunks have poor metadata and may rank lower.
**Mitigation:** The fallback ensures nothing is lost; metadata quality is the tradeoff.

## Dependency Mapping Failures

### 9. Incomplete call chains
**Problem:** The call chain extractor uses regex (`CALL \w+`) which misses function-style calls (e.g., `X = DLANGE(...)`) and computed/indirect calls.
**Impact:** Dependency graphs are incomplete; some edges missing.
**Mitigation:** A proper Fortran AST parser (tree-sitter-fortran) would capture all call types.

### 10. Circular dependency display
**Problem:** BFS traversal correctly prevents infinite loops via visited set, but the UI doesn't indicate that a node was already visited (showing it as a leaf instead).
**Impact:** Users may think a routine has no callees when it was simply already shown.
**Mitigation:** Add a "visited" indicator in the dependency tree UI.

## Infrastructure Edge Cases

### 11. API rate limits
**Problem:** Heavy concurrent usage could hit OpenAI embedding rate limits or Anthropic token limits.
**Impact:** 429 errors returned to users.
**Mitigation:** Add retry with exponential backoff; embedding caching for repeated queries.

### 12. Database connection exhaustion
**Problem:** Each query opens a new psycopg2 connection. Under load, this could exhaust the Supabase connection pool (default: 15-20 connections).
**Impact:** Database connection errors.
**Mitigation:** Switch to connection pooling (psycopg2.pool or SQLAlchemy).

### 13. Empty or nonsense queries
**Problem:** Empty strings, single characters, or completely unrelated queries (e.g., "What's the weather?") return low-relevance results.
**Impact:** Wasted API calls; confusing results.
**Mitigation:** Add input validation (minimum length) and low-relevance threshold filtering.
