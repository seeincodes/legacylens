#!/usr/bin/env python3
"""Pre-generate and cache LLM explanations for all routines.

Run after ingestion to warm the routine_explanations DB cache so users
never wait for LLM generation on first request.

Usage:
    cd backend
    python scripts/pregenerate_explanations.py                  # explain only (all routines)
    python scripts/pregenerate_explanations.py --actions explain eli5 document
    python scripts/pregenerate_explanations.py --largest 100    # top 100 by code length
    python scripts/pregenerate_explanations.py --limit 50       # first 50 alphabetically
"""
import argparse
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from app.services.understanding import (
    explain_routine,
    explain_routine_eli5,
    generate_documentation,
    translate_routine,
    get_use_cases,
)

ACTION_MAP = {
    "explain": explain_routine,
    "eli5": explain_routine_eli5,
    "document": generate_documentation,
    "translate": lambda name: translate_routine(name, target_language="python"),
    "use-cases": get_use_cases,
}


def get_all_routine_names(limit: int | None = None, largest: int | None = None) -> list[str]:
    import psycopg2
    from app.config import settings

    conn = psycopg2.connect(settings.database_url)
    cur = conn.cursor()
    if largest:
        sql = """SELECT subroutine_name FROM code_chunks
                 WHERE subroutine_name IS NOT NULL
                 ORDER BY LENGTH(content) DESC
                 LIMIT %s"""
        cur.execute(sql, (largest,))
    else:
        sql = """SELECT DISTINCT subroutine_name FROM code_chunks
                 WHERE subroutine_name IS NOT NULL
                 ORDER BY subroutine_name"""
        if limit:
            sql += f" LIMIT {limit}"
        cur.execute(sql)
    names = [row[0] for row in cur.fetchall() if row[0]]
    cur.close()
    conn.close()
    return names


def get_cached_set(action: str) -> set[str]:
    """Fetch all routine names already cached for an action in one query."""
    import psycopg2
    from app.config import settings

    conn = psycopg2.connect(settings.database_url)
    cur = conn.cursor()
    cur.execute(
        "SELECT UPPER(subroutine_name) FROM routine_explanations WHERE action = %s",
        (action,),
    )
    cached = {row[0] for row in cur.fetchall()}
    cur.close()
    conn.close()
    return cached


def main():
    parser = argparse.ArgumentParser(description="Pre-generate LLM explanations")
    parser.add_argument(
        "--actions", nargs="+", default=["explain"],
        choices=list(ACTION_MAP.keys()),
        help="Which actions to pre-generate (default: explain)",
    )
    parser.add_argument("--limit", type=int, default=None, help="Max routines to process (alphabetical)")
    parser.add_argument("--largest", type=int, default=None, help="Only the N largest routines by code length")
    args = parser.parse_args()

    names = get_all_routine_names(limit=args.limit, largest=args.largest)
    print(f"Found {len(names)} routines, actions: {args.actions}\n", flush=True)

    for action in args.actions:
        fn = ACTION_MAP[action]
        cached_names = get_cached_set(action)
        total = len(names)
        to_generate = [n for n in names if n.upper() not in cached_names]
        skipped = total - len(to_generate)
        generated = 0
        failed = 0

        print(f"  [{action}] {skipped} already cached, {len(to_generate)} to generate", flush=True)

        for i, name in enumerate(to_generate, 1):
            try:
                result = fn(name)
                if result:
                    generated += 1
                else:
                    failed += 1
            except Exception as exc:
                failed += 1
                print(f"  [{action}] FAIL {name}: {exc}", flush=True)
                time.sleep(2)
                continue

            if i % 10 == 0 or i == len(to_generate):
                print(f"  [{action}] {i}/{len(to_generate)} (generated={generated}, failed={failed})", flush=True)

            time.sleep(0.5)

        print(f"\n  [{action}] Done: {generated} generated, {skipped} already cached, {failed} failed\n", flush=True)

    print("Pre-generation complete.", flush=True)


if __name__ == "__main__":
    main()
