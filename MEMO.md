# LegacyLens - Architecture Memo

## Project Summary

LegacyLens is a RAG system that indexes the LAPACK Fortran codebase (~670 files, ~100K LOC) and allows developers to query it using natural language. It returns relevant code snippets with file/line references and LLM-generated explanations.

## Key Architecture Decisions

### 1. Why LAPACK as the Target Codebase

LAPACK was chosen over GnuCOBOL, gfortran, BLAS standalone, and OpenCOBOL Contrib because:

- **It is actual legacy Fortran code.** GnuCOBOL and OpenCOBOL Contrib are compilers written in C -- they compile COBOL but contain almost no COBOL source. gfortran is C++. Only LAPACK and BLAS are genuine Fortran.
- **Exceptional documentation quality.** Every file has a ~100-line header block documenting purpose, parameters, and algorithm. This 10:1 documentation-to-code ratio means RAG retrieval returns rich, informative results.
- **Perfect chunking boundaries.** One subroutine per file eliminates chunking ambiguity entirely.
- **Rich query potential.** Deep call chains (DGESV -> DGETRF -> DGETRS), systematic naming conventions (XYYZZZ), and algorithm families enable diverse, interesting queries.
- **Real-world significance.** LAPACK powers NumPy, MATLAB, R, and most scientific computing -- reviewers will recognize it.

Scoped to double-precision routines (`D*` files) + BLAS to stay within a manageable ~670 files while exceeding the 10K LOC / 50 file minimums.

### 2. Why pgvector via Supabase (Not Pinecone/Qdrant/ChromaDB)

The deciding factor is **metadata filtering**. Code queries frequently filter by file type, subroutine name, routine category, or precision -- full SQL `WHERE`/`JOIN` clauses handle this natively. Alternatives:

- **Pinecone:** Free tier pauses after 3 weeks idle (demo goes cold). Closed source, vendor lock-in.
- **Qdrant:** Free tier suspends after 1 week idle. Better search API but needs a keep-alive workaround.
- **ChromaDB:** Fastest prototype but embedded mode isn't publicly accessible. Basic metadata filtering.
- **pgvector/Supabase:** No idle suspension. Free tier includes auth, REST API, storage. Vectors + metadata + app data in one service. Hybrid search via `tsvector` + pgvector + RRF.

### 3. Why OpenAI text-embedding-3-small (Not Voyage code-3)

For MVP: OpenAI small at $0.02/1M tokens vs Voyage code-3 at $0.18/1M tokens. Voyage scores 92% on code retrieval vs OpenAI's ~77%, but the 14% gap is partially compensated by hybrid search (BM25 catches exact Fortran identifiers). The 8K context fits individual LAPACK subroutines. Upgrade path to Voyage code-3 is straightforward for the final submission (200M free tokens available).

### 4. Why LlamaIndex (Not LangChain/Haystack/Custom)

LlamaIndex has an AST-based `CodeSplitter` using tree-sitter that parses along subroutine/function boundaries. LangChain uses regex-based splitting. Haystack has no code splitter. LlamaIndex also benchmarks 35% better on retrieval accuracy with lower framework overhead (~6ms vs LangChain's ~10ms).

### 5. Why Claude Haiku 4.5 (Not GPT-4o-mini/Open Source)

Claude leads SWE-bench (Opus at 80.9%, Sonnet at ~72%) and SWE-bench Multilingual (7/8 languages). Haiku 4.5 at $1/$5 per 1M tokens is cost-effective for most queries. Claude's 200K context window allows including large code contexts. GPT-4o-mini is cheaper ($0.15/$0.60) but less capable on code understanding. Open source models lag significantly on SWE-bench (~43%).

## Chunking Strategy

For Fortran (LAPACK/BLAS):
- Chunk by SUBROUTINE/FUNCTION boundary (one per file = one chunk per file)
- Include comment header blocks (Purpose, Parameters, Algorithm) as part of each chunk
- Prepend metadata as text prefix: `"File: dgesv.f | Subroutine: DGESV | Type: Driver | Precision: Double"`
- Target chunk size: 500-1500 tokens (natural fit for most LAPACK subroutines)

## Retrieval Pipeline

1. **Embed query** using same model as ingestion (OpenAI text-embedding-3-small)
2. **Vector search** (top-k=10, cosine similarity via HNSW index)
3. **Keyword search** (BM25 via tsvector for exact identifier matching)
4. **RRF fusion** to merge vector + keyword results
5. **Re-rank** to top-5 by combined relevance score
6. **Context assembly** -- top-5 chunks + surrounding code from same files
7. **LLM synthesis** -- Claude Haiku generates answer with [file:line] citations

## Known Failure Modes

- **Precision variant confusion:** Queries may return S/D/C/Z variants of the same routine. Mitigate by filtering to double-precision by default.
- **Generic queries return too many results:** "Find all subroutines" matches everything. Mitigate with relevance score thresholds.
- **Exact identifier queries miss:** Embedding models may not perfectly match "DGESV" as a search term. Mitigate with hybrid BM25 search.
- **LLM hallucination on line numbers:** Claude may invent line numbers not in the retrieved context. Mitigate by only displaying line numbers from the actual chunk metadata, not the LLM output.
