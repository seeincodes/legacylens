# LegacyLens - Error & Fix Log

Track issues encountered during development and their resolutions.

---

## Template

### [DATE] - Brief Description
**Error:** What went wrong
**Context:** What you were doing when it happened
**Root Cause:** Why it happened
**Fix:** How you resolved it
**Prevention:** How to avoid it in the future

---

## Log

*No errors logged yet. Development has not started.*

---

## Common Issues to Watch For

### pgvector / Supabase
- **Embedding dimension mismatch:** Ensure the `VECTOR(1536)` column matches the embedding model output. If switching to Voyage code-3 (1024 dims), the column must be recreated.
- **HNSW index build time:** For 670+ rows with 1536-dim vectors, index creation should be fast (<1 min). If slow, check if the table has unexpected row counts from duplicate ingestion.
- **Supabase free tier limits:** 500 MB storage, 2 projects max. Monitor usage in the Supabase dashboard.

### OpenAI Embedding API
- **Rate limits:** Free tier: 100 RPM / 40K TPM. Tier 1: 3,000 RPM / 1M TPM. Batch all chunks and respect limits.
- **Token truncation:** text-embedding-3-small has 8K token context. LAPACK subroutines rarely exceed this, but verify no chunks are silently truncated.

### Claude API
- **Streaming errors:** If the connection drops mid-stream, implement retry logic. Don't retry the full query -- cache the retrieved chunks and only retry the LLM call.
- **Context overflow:** 200K token limit is generous but if concatenating many large chunks, verify total input stays within limits.

### LlamaIndex
- **tree-sitter Fortran parser:** Ensure `tree-sitter-fortran` is installed and compatible. Fortran 77 fixed-format (columns 1-72) vs free-format (.f90) may need different parser configurations.
- **CodeSplitter language support:** Verify LlamaIndex's CodeSplitter supports Fortran. If not, fall back to custom regex-based splitting on `SUBROUTINE` / `FUNCTION` / `END` keywords.

### Deployment
- **CORS issues:** Ensure the FastAPI backend allows requests from the Vercel frontend domain.
- **Cold starts:** Railway/Render free tier may have cold start delays. First request after idle may take 10-30 seconds.
- **Environment variables:** Double-check all secrets are set in deployment platform. Missing `OPENAI_API_KEY` will cause silent embedding failures.
