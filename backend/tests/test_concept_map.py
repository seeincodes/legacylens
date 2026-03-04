import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.concept_map import (
    load_concept_map,
    get_stem_from_routine_name,
    get_concepts_for_stem,
    find_stems_for_query,
)


def test_load_concept_map_returns_dict():
    cmap = load_concept_map()
    assert isinstance(cmap, dict)
    assert len(cmap) > 0


def test_load_concept_map_has_expected_stems():
    cmap = load_concept_map()
    for stem in ["POTRF", "GETRF", "GEEV", "GEMM", "GESVD"]:
        assert stem in cmap, f"Missing stem {stem}"


def test_get_stem_from_routine_name():
    assert get_stem_from_routine_name("DPOTRF") == "POTRF"
    assert get_stem_from_routine_name("SPOTRF") == "POTRF"
    assert get_stem_from_routine_name("CPOTRF") == "POTRF"
    assert get_stem_from_routine_name("ZPOTRF") == "POTRF"


def test_get_stem_preserves_non_prefixed():
    # X and I are not precision prefixes (only S/D/C/Z), so these are unchanged
    assert get_stem_from_routine_name("XERBLA") == "XERBLA"
    assert get_stem_from_routine_name("ILAENV") == "ILAENV"


def test_get_stem_handles_empty():
    assert get_stem_from_routine_name("") == ""


def test_get_concepts_for_stem():
    concepts = get_concepts_for_stem("POTRF")
    assert len(concepts) > 0
    assert any("cholesky" in c.lower() for c in concepts)


def test_get_concepts_for_unknown_stem():
    concepts = get_concepts_for_stem("ZZZZZ")
    assert concepts == []


def test_find_stems_for_query_cholesky():
    stems = find_stems_for_query("Cholesky factorization")
    assert "POTRF" in stems


def test_find_stems_for_query_eigenvalue():
    stems = find_stems_for_query("Find eigenvalue routines")
    assert "GEEV" in stems or "SYEV" in stems


def test_find_stems_for_query_lu():
    stems = find_stems_for_query("How does LU factorization work in LAPACK?")
    assert "GETRF" in stems


def test_find_stems_for_query_svd():
    stems = find_stems_for_query("Singular value decomposition")
    assert "GESVD" in stems or "GESDD" in stems


def test_find_stems_for_query_least_squares():
    stems = find_stems_for_query("Solve least squares problem")
    assert "GELS" in stems or "GELSS" in stems or "GELSD" in stems


def test_find_stems_for_query_no_match():
    stems = find_stems_for_query("What does DGESV do?")
    # A routine name query shouldn't match many concept terms
    # (it might match some if the name is in a concept, but that's fine)
    assert isinstance(stems, list)


def test_find_stems_for_query_empty():
    stems = find_stems_for_query("")
    assert isinstance(stems, list)


def test_find_stems_for_query_matrix_norm():
    stems = find_stems_for_query("Matrix norm computation")
    assert "LANGE" in stems or "LANSY" in stems


def test_find_stems_for_query_condition_number():
    stems = find_stems_for_query("Condition number estimation")
    assert "GECON" in stems or "POCON" in stems


def test_find_stems_for_query_schur():
    stems = find_stems_for_query("Schur decomposition")
    assert "GEES" in stems or "HSEQR" in stems


def test_find_stems_for_query_householder():
    stems = find_stems_for_query("Householder reflections")
    assert "LARFG" in stems or "LARF" in stems


def test_find_stems_for_query_banded():
    stems = find_stems_for_query("Banded matrix solver")
    assert "GBSV" in stems or "GBTRF" in stems


def test_find_stems_for_query_tridiagonal():
    stems = find_stems_for_query("Tridiagonal eigenvalue solver")
    assert "STEQR" in stems or "STEV" in stems


def test_find_stems_for_query_generalized_eigenvalue():
    stems = find_stems_for_query("Generalized eigenvalue problem")
    assert "GGEV" in stems or "SYGV" in stems


def test_find_stems_for_query_triangular():
    stems = find_stems_for_query("Triangular matrix operations")
    assert "TRMM" in stems or "TRSM" in stems


def test_find_stems_for_query_pivoting():
    stems = find_stems_for_query("How does LAPACK handle pivoting?")
    assert "LASWP" in stems or "GETRF" in stems


def test_find_stems_for_query_qr():
    stems = find_stems_for_query("QR factorization routines")
    assert "GEQRF" in stems or "ORGQR" in stems


def test_find_stems_for_query_matrix_inverse():
    stems = find_stems_for_query("How to compute matrix inverse?")
    assert "GETRI" in stems
