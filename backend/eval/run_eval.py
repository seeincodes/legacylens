"""
Retrieval evaluation script for LegacyLens.

Runs ground truth queries through the retrieval pipeline and measures
Precision@5, Recall@5, and Mean Reciprocal Rank (MRR).

Usage:
    cd backend
    python -m eval.run_eval                 # full eval
    python -m eval.run_eval --expand        # with query expansion
    python -m eval.run_eval --top-k 10      # evaluate at top-10
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Ensure the backend package is importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.retrieval import search  # noqa: E402


def load_ground_truth(path: str | None = None) -> list[dict]:
    if path is None:
        path = str(Path(__file__).with_name("ground_truth.json"))
    with open(path) as f:
        return json.load(f)


def evaluate_query(
    entry: dict,
    top_k: int = 5,
    expand: bool = False,
) -> dict:
    """Run a single query and compute metrics."""
    query = entry["query"]
    expected = {r.upper() for r in entry["expected_routines"]}
    related = {r.upper() for r in entry.get("related_routines", [])}
    all_relevant = expected | related

    start = time.perf_counter()
    results = search(query=query, top_k=top_k, expand=expand)
    latency_ms = (time.perf_counter() - start) * 1000

    retrieved = []
    for chunk in results:
        name = (chunk.subroutine_name or "").upper()
        retrieved.append(name)

    # Precision@K: fraction of retrieved that are relevant
    relevant_retrieved = [r for r in retrieved if r in all_relevant]
    precision = len(relevant_retrieved) / len(retrieved) if retrieved else 0.0

    # Recall@K: fraction of expected routines found
    expected_found = [r for r in retrieved if r in expected]
    recall = len(set(expected_found)) / len(expected) if expected else 0.0

    # Reciprocal Rank: 1/rank of first relevant result
    rr = 0.0
    for i, name in enumerate(retrieved):
        if name in all_relevant:
            rr = 1.0 / (i + 1)
            break

    return {
        "id": entry["id"],
        "query": query,
        "category": entry.get("category", ""),
        "expected": sorted(expected),
        "retrieved": retrieved,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "reciprocal_rank": round(rr, 4),
        "latency_ms": round(latency_ms, 1),
    }


def run_evaluation(
    ground_truth_path: str | None = None,
    top_k: int = 5,
    expand: bool = False,
) -> dict:
    """Run full evaluation and return aggregate metrics."""
    entries = load_ground_truth(ground_truth_path)
    results = []
    latencies = []

    print(f"Running evaluation: {len(entries)} queries, top_k={top_k}, expand={expand}")
    print("-" * 70)

    for entry in entries:
        result = evaluate_query(entry, top_k=top_k, expand=expand)
        results.append(result)
        latencies.append(result["latency_ms"])

        status = "HIT" if result["reciprocal_rank"] > 0 else "MISS"
        print(
            f"  [{status}] Q{result['id']:02d} P@{top_k}={result['precision']:.2f} "
            f"R@{top_k}={result['recall']:.2f} RR={result['reciprocal_rank']:.2f} "
            f"({result['latency_ms']:.0f}ms) {result['query'][:50]}"
        )

    # Aggregate metrics
    n = len(results)
    avg_precision = sum(r["precision"] for r in results) / n
    avg_recall = sum(r["recall"] for r in results) / n
    mrr = sum(r["reciprocal_rank"] for r in results) / n
    hit_rate = sum(1 for r in results if r["reciprocal_rank"] > 0) / n

    latencies.sort()
    p50 = latencies[len(latencies) // 2] if latencies else 0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0

    # Per-category breakdown
    categories: dict[str, list[dict]] = {}
    for r in results:
        cat = r.get("category", "unknown")
        categories.setdefault(cat, []).append(r)

    category_metrics = {}
    for cat, cat_results in categories.items():
        cn = len(cat_results)
        category_metrics[cat] = {
            "count": cn,
            "precision": round(sum(r["precision"] for r in cat_results) / cn, 4),
            "recall": round(sum(r["recall"] for r in cat_results) / cn, 4),
            "mrr": round(sum(r["reciprocal_rank"] for r in cat_results) / cn, 4),
        }

    summary = {
        "config": {"top_k": top_k, "expand": expand, "num_queries": n},
        "aggregate": {
            "precision_at_k": round(avg_precision, 4),
            "recall_at_k": round(avg_recall, 4),
            "mrr": round(mrr, 4),
            "hit_rate": round(hit_rate, 4),
        },
        "latency": {
            "p50_ms": round(p50, 1),
            "p95_ms": round(p95, 1),
            "min_ms": round(min(latencies), 1) if latencies else 0,
            "max_ms": round(max(latencies), 1) if latencies else 0,
        },
        "by_category": category_metrics,
        "details": results,
    }

    print("-" * 70)
    print(f"  Precision@{top_k}: {avg_precision:.4f}")
    print(f"  Recall@{top_k}:    {avg_recall:.4f}")
    print(f"  MRR:             {mrr:.4f}")
    print(f"  Hit Rate:        {hit_rate:.4f}")
    print(f"  Latency p50:     {p50:.0f}ms")
    print(f"  Latency p95:     {p95:.0f}ms")

    for cat, cm in category_metrics.items():
        print(f"  [{cat}] P={cm['precision']:.2f} R={cm['recall']:.2f} MRR={cm['mrr']:.2f} (n={cm['count']})")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Run LegacyLens retrieval evaluation")
    parser.add_argument("--ground-truth", type=str, default=None, help="Path to ground truth JSON")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to retrieve")
    parser.add_argument("--expand", action="store_true", help="Enable query expansion")
    parser.add_argument("--output", type=str, default=None, help="Save results to JSON file")
    args = parser.parse_args()

    summary = run_evaluation(
        ground_truth_path=args.ground_truth,
        top_k=args.top_k,
        expand=args.expand,
    )

    if args.output:
        with open(args.output, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
