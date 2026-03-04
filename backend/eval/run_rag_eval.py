"""
RAG answer pipeline evaluation script for LegacyLens.

Runs full RAG (retrieval + generation) on golden queries and evaluates answer quality
using expected facts, citation validity, and retrieval relevance.

Usage:
    cd backend
    python -m eval.run_rag_eval                    # full RAG eval
    python -m eval.run_rag_eval --expand --rerank  # with query expansion + rerank
    python -m eval.run_rag_eval --output results.json
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Ensure the backend package is importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.retrieval import search  # noqa: E402
from app.services.generation import generate_answer, validate_references  # noqa: E402


def load_rag_ground_truth(path: str | None = None) -> list[dict]:
    if path is None:
        path = str(Path(__file__).with_name("rag_ground_truth.json"))
    with open(path) as f:
        return json.load(f)


def count_facts_in_answer(answer: str, expected_facts: list[str]) -> int:
    """Count how many expected facts (case-insensitive substring) appear in the answer."""
    answer_lower = answer.lower()
    count = 0
    for fact in expected_facts:
        if fact.lower() in answer_lower:
            count += 1
    return count


def has_valid_citations(answer: str, chunks: list) -> bool:
    """Check that answer has no unverified citations."""
    _, has_unverified = validate_references(answer, chunks)
    return not has_unverified


def evaluate_rag_query(
    entry: dict,
    top_k: int = 5,
    expand: bool = False,
    rerank: bool = True,
    brief: bool = False,
) -> dict:
    """Run full RAG pipeline for one query and evaluate the answer."""
    query = entry["query"]
    expected_facts = entry.get("expected_facts", [])
    min_facts = entry.get("min_facts", 2)
    expected_routines = {r.upper() for r in entry.get("expected_routines", [])}

    t_start = time.perf_counter()
    chunks = search(query=query, top_k=top_k, expand=expand, rerank=rerank)
    retrieval_ms = (time.perf_counter() - t_start) * 1000

    t_gen = time.perf_counter()
    try:
        answer = generate_answer(query, chunks, brief=brief)
    except Exception as e:
        answer = f"Error: {e}"
    generation_ms = (time.perf_counter() - t_gen) * 1000
    total_ms = retrieval_ms + generation_ms

    # Fact coverage
    facts_found = count_facts_in_answer(answer, expected_facts)
    fact_coverage = facts_found / len(expected_facts) if expected_facts else 1.0
    fact_pass = facts_found >= min_facts

    # Citation validity
    citations_valid = has_valid_citations(answer, chunks)

    # Retrieval relevance: did we get expected routines?
    retrieved = [(c.subroutine_name or "").upper() for c in chunks]
    expected_found = [r for r in retrieved if r in expected_routines]
    retrieval_hit = len(set(expected_found)) > 0 if expected_routines else True

    return {
        "id": entry["id"],
        "query": query,
        "category": entry.get("category", ""),
        "answer": answer[:500] + "..." if len(answer) > 500 else answer,
        "facts_found": facts_found,
        "facts_total": len(expected_facts),
        "fact_coverage": round(fact_coverage, 4),
        "fact_pass": fact_pass,
        "citations_valid": citations_valid,
        "retrieval_hit": retrieval_hit,
        "retrieved_routines": retrieved[:top_k],
        "retrieval_ms": round(retrieval_ms, 1),
        "generation_ms": round(generation_ms, 1),
        "total_ms": round(total_ms, 1),
    }


def run_rag_evaluation(
    ground_truth_path: str | None = None,
    top_k: int = 5,
    expand: bool = False,
    rerank: bool = True,
    brief: bool = False,
) -> dict:
    """Run full RAG evaluation and return aggregate metrics."""
    entries = load_rag_ground_truth(ground_truth_path)
    results = []

    print(f"Running RAG evaluation: {len(entries)} queries, top_k={top_k}, expand={expand}, rerank={rerank}")
    print("-" * 80)

    for entry in entries:
        result = evaluate_rag_query(
            entry, top_k=top_k, expand=expand, rerank=rerank, brief=brief
        )
        results.append(result)

        pass_status = "PASS" if (result["fact_pass"] and result["citations_valid"]) else "FAIL"
        print(
            f"  [{pass_status}] Q{result['id']:02d} facts={result['facts_found']}/{result['facts_total']} "
            f"cites_ok={result['citations_valid']} ret_hit={result['retrieval_hit']} "
            f"({result['total_ms']:.0f}ms) {result['query'][:45]}"
        )

    # Aggregate metrics
    n = len(results)
    fact_pass_rate = sum(1 for r in results if r["fact_pass"]) / n
    cite_pass_rate = sum(1 for r in results if r["citations_valid"]) / n
    retrieval_hit_rate = sum(1 for r in results if r["retrieval_hit"]) / n
    full_pass_rate = sum(
        1 for r in results if r["fact_pass"] and r["citations_valid"]
    ) / n
    avg_fact_coverage = sum(r["fact_coverage"] for r in results) / n

    latencies = [r["total_ms"] for r in results]
    latencies.sort()
    p50 = latencies[len(latencies) // 2] if latencies else 0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0

    summary = {
        "config": {
            "top_k": top_k,
            "expand": expand,
            "rerank": rerank,
            "brief": brief,
            "num_queries": n,
        },
        "aggregate": {
            "fact_pass_rate": round(fact_pass_rate, 4),
            "citation_pass_rate": round(cite_pass_rate, 4),
            "retrieval_hit_rate": round(retrieval_hit_rate, 4),
            "full_pass_rate": round(full_pass_rate, 4),
            "avg_fact_coverage": round(avg_fact_coverage, 4),
        },
        "latency": {
            "p50_ms": round(p50, 1),
            "p95_ms": round(p95, 1),
            "min_ms": round(min(latencies), 1) if latencies else 0,
            "max_ms": round(max(latencies), 1) if latencies else 0,
        },
        "details": results,
    }

    print("-" * 80)
    print(f"  Fact pass rate:      {fact_pass_rate:.2%}")
    print(f"  Citation pass rate:  {cite_pass_rate:.2%}")
    print(f"  Retrieval hit rate:  {retrieval_hit_rate:.2%}")
    print(f"  Full pass rate:      {full_pass_rate:.2%}")
    print(f"  Avg fact coverage:   {avg_fact_coverage:.2%}")
    print(f"  Latency p50:         {p50:.0f}ms")
    print(f"  Latency p95:         {p95:.0f}ms")

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Run LegacyLens RAG answer pipeline evaluation"
    )
    parser.add_argument(
        "--ground-truth",
        type=str,
        default=None,
        help="Path to RAG ground truth JSON",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of chunks to retrieve",
    )
    parser.add_argument(
        "--expand",
        action="store_true",
        help="Enable query expansion",
    )
    parser.add_argument(
        "--rerank",
        action="store_true",
        default=True,
        help="Enable LLM re-ranking (default: True)",
    )
    parser.add_argument(
        "--no-rerank",
        action="store_true",
        help="Disable LLM re-ranking",
    )
    parser.add_argument(
        "--brief",
        action="store_true",
        help="Use brief answer mode",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Save results to JSON file",
    )
    args = parser.parse_args()

    rerank = args.rerank and not args.no_rerank

    summary = run_rag_evaluation(
        ground_truth_path=args.ground_truth,
        top_k=args.top_k,
        expand=args.expand,
        rerank=rerank,
        brief=args.brief,
    )

    if args.output:
        with open(args.output, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
