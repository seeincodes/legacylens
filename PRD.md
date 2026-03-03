# LegacyLens - Product Requirements Document

## Overview

LegacyLens is a RAG-powered system that makes the LAPACK legacy Fortran codebase queryable and understandable through natural language. It ingests ~670 Fortran files (~100K+ LOC), chunks them by subroutine boundaries, generates embeddings, stores them in a vector database, and provides a web interface for developers to ask questions about the code.

## Problem Statement

Enterprise systems running on legacy languages (Fortran, COBOL) power critical infrastructure, but few engineers understand these codebases. LAPACK -- the foundational linear algebra library used by NumPy, MATLAB, and R -- contains decades of mathematical algorithms in Fortran 77/90 that are difficult to navigate without deep domain expertise.

## Target Users

- Developers working with or maintaining legacy Fortran codebases
- Engineers using LAPACK indirectly (via NumPy/SciPy) who need to understand underlying algorithms
- Students and researchers exploring numerical linear algebra implementations

## MVP Requirements (24-Hour Deadline)

All items required to pass:

- [ ] Ingest LAPACK codebase (double-precision `SRC/` + `BLAS/SRC/`, ~670 Fortran files)
- [ ] Chunk code files with syntax-aware splitting (subroutine/function boundaries)
- [ ] Generate embeddings for all chunks (OpenAI text-embedding-3-small)
- [ ] Store embeddings in pgvector via Supabase
- [ ] Implement semantic search across the codebase
- [ ] Natural language query interface (web UI)
- [ ] Return relevant code snippets with file/line references
- [ ] Basic answer generation using retrieved context (Claude Haiku 4.5)
- [ ] Deployed and publicly accessible

## Final Submission Features

Code Understanding Features (implement 4+ of 8):

- [ ] Code Explanation -- explain what a subroutine does in plain English
- [ ] Dependency Mapping -- show call chains (DGESV -> DGETRF -> DGETRS)
- [ ] Pattern Detection -- find similar routines across the codebase
- [ ] Impact Analysis -- what would be affected if this routine changes
- [ ] Documentation Generation -- generate docs for undocumented code
- [ ] Translation Hints -- suggest modern language equivalents
- [ ] Bug Pattern Search -- find potential issues based on known patterns
- [ ] Business Logic Extract -- identify and explain algorithm logic

## Performance Targets

| Metric | Target |
|---|---|
| Retrieval latency | <3 seconds (embedding + DB lookup) |
| Answer generation | Streaming via SSE (5–30s total, depends on LLM response length) |
| Retrieval precision | >70% relevant chunks in top-5 |
| Codebase coverage | 100% of files indexed |
| Ingestion throughput | 100K+ LOC in <5 minutes |
| Answer accuracy | Correct file/line references |

## Scope Boundaries

**In scope:**
- LAPACK double-precision routines (`D*` files from `SRC/`)
- BLAS reference implementation (`BLAS/SRC/`)
- Web-based query interface
- Semantic + keyword hybrid search
- LLM-generated answers with code citations

**Out of scope:**
- Real-time codebase updates / incremental indexing
- Code editing or modification capabilities
- Multi-language support (Fortran only for this project)
- User authentication / multi-tenancy
