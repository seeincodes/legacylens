#!/usr/bin/env python3
"""One-time script to ingest LAPACK source into pgvector."""
import sys
import os
import time

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
    if not os.path.isdir(DATA_DIR):
        print(f"ERROR: Data directory not found: {DATA_DIR}")
        print("Run download_lapack.sh first.")
        sys.exit(1)

    files = discover_fortran_files(DATA_DIR)

    print(f"Found {len(files)} Fortran files")

    all_chunks = []
    for fpath in files:
        rel_path = os.path.relpath(fpath, DATA_DIR)
        with open(fpath, "r", errors="replace") as f:
            content = f.read()
        chunks = parse_fortran_file(content, rel_path)
        all_chunks.extend(chunks)

    print(f"Parsed into {len(all_chunks)} chunks")

    texts = [build_chunk_text(c) for c in all_chunks]
    print("Generating embeddings...")
    start = time.time()
    embeddings = generate_embeddings(texts)
    elapsed = time.time() - start
    print(f"Embedding complete in {elapsed:.1f}s")

    print("Storing in database...")
    store_chunks(all_chunks, embeddings)
    print(f"Done! Stored {len(all_chunks)} chunks.")


if __name__ == "__main__":
    main()
