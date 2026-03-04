import json
from functools import lru_cache
from pathlib import Path

CONCEPT_MAP_PATH = Path(__file__).parent.parent / "data" / "concept_map.json"


@lru_cache(maxsize=1)
def load_concept_map() -> dict[str, list[str]]:
    with open(CONCEPT_MAP_PATH) as f:
        return json.load(f)


def get_stem_from_routine_name(name: str) -> str:
    """Strip precision prefix (S/D/C/Z) to get the routine stem."""
    upper = name.upper()
    if upper and upper[0] in "SDCZ" and len(upper) > 1:
        return upper[1:]
    return upper


def get_concepts_for_stem(stem: str) -> list[str]:
    """Return concept terms for a routine stem (e.g. 'POTRF' -> ['Cholesky ...'])."""
    cmap = load_concept_map()
    return cmap.get(stem.upper(), [])


def find_stems_for_query(query: str) -> list[str]:
    """Return routine stems whose concept terms match the query.

    Uses bidirectional case-insensitive substring matching:
    a concept matches if it appears in the query OR the query appears in the concept.
    Punctuation is stripped from the query before matching.
    """
    import re

    cmap = load_concept_map()
    # Strip punctuation so "pivoting?" matches "pivoting"
    query_clean = re.sub(r"[^\w\s]", "", query).lower()
    matches = []
    for stem, concepts in cmap.items():
        for concept in concepts:
            concept_lower = concept.lower()
            if concept_lower in query_clean or query_clean in concept_lower:
                matches.append(stem)
                break
    return matches
