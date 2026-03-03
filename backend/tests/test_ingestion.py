import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.ingestion import parse_fortran_file, extract_metadata, discover_fortran_files

SAMPLE_FORTRAN = """\
*> \\brief <b> DGESV computes the solution to system of linear equations A * X = B</b>
*
*  Purpose
*  =======
*  DGESV computes the solution to a real system of linear equations
*     A * X = B,
*  where A is an N-by-N matrix and X and B are N-by-NRHS matrices.
*
      SUBROUTINE DGESV( N, NRHS, A, LDA, IPIV, B, LDB, INFO )
*
*     .. Scalar Arguments ..
      INTEGER            INFO, LDA, LDB, N, NRHS
*     ..
*     .. Array Arguments ..
      INTEGER            IPIV( * )
      DOUBLE PRECISION   A( LDA, * ), B( LDB, * )
*
      EXTERNAL           DGETRF, DGETRS
*
      CALL DGETRF( N, N, A, LDA, IPIV, INFO )
      CALL DGETRS( 'No transpose', N, NRHS, A, LDA, IPIV, B, LDB, INFO )
*
      RETURN
      END
"""


def test_parse_fortran_extracts_subroutine():
    chunks = parse_fortran_file(SAMPLE_FORTRAN, "SRC/dgesv.f")
    assert len(chunks) >= 1
    assert chunks[0]["subroutine_name"] == "DGESV"


def test_extract_metadata_gets_calls():
    meta = extract_metadata(SAMPLE_FORTRAN, "SRC/dgesv.f")
    assert "DGETRF" in meta["calls"]
    assert "DGETRS" in meta["calls"]


def test_extract_metadata_detects_precision():
    meta = extract_metadata(SAMPLE_FORTRAN, "SRC/dgesv.f")
    assert meta["precision_type"] == "double"


def test_single_precision_detected():
    chunks = parse_fortran_file(SAMPLE_FORTRAN, "SRC/sgesv.f")
    assert chunks[0]["precision_type"] == "single"


def test_chunk_includes_content():
    chunks = parse_fortran_file(SAMPLE_FORTRAN, "SRC/dgesv.f")
    assert "SUBROUTINE DGESV" in chunks[0]["content"]


def test_chunk_has_line_numbers():
    chunks = parse_fortran_file(SAMPLE_FORTRAN, "SRC/dgesv.f")
    assert chunks[0]["line_start"] >= 1
    assert chunks[0]["line_end"] >= chunks[0]["line_start"]


MULTI_SUB_FORTRAN = """\
      SUBROUTINE FOO( N )
      INTEGER N
      CALL HELPER_A( N )
      RETURN
      END SUBROUTINE FOO

      SUBROUTINE BAR( M )
      INTEGER M
      CALL HELPER_B( M )
      CALL HELPER_C( M )
      RETURN
      END SUBROUTINE BAR
"""


def test_per_chunk_calls_extraction():
    """Each chunk should only contain calls from its own subroutine, not the whole file."""
    chunks = parse_fortran_file(MULTI_SUB_FORTRAN, "SRC/test.f")
    assert len(chunks) == 2

    foo_chunk = next(c for c in chunks if c["subroutine_name"] == "FOO")
    bar_chunk = next(c for c in chunks if c["subroutine_name"] == "BAR")

    assert "HELPER_A" in foo_chunk["metadata"]["calls"]
    assert "HELPER_B" not in foo_chunk["metadata"]["calls"]

    assert "HELPER_B" in bar_chunk["metadata"]["calls"]
    assert "HELPER_C" in bar_chunk["metadata"]["calls"]
    assert "HELPER_A" not in bar_chunk["metadata"]["calls"]


def test_discover_finds_f90_and_f95_files():
    """discover_fortran_files should find .f, .f90, .f95, and .f03 files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create files with various extensions
        for name in ["test.f", "test.f90", "test.f95", "test.f03", "test.c", "test.py"]:
            open(os.path.join(tmpdir, name), "w").close()

        found = discover_fortran_files(tmpdir)
        basenames = [os.path.basename(f) for f in found]

        assert "test.f" in basenames
        assert "test.f90" in basenames
        assert "test.f95" in basenames
        assert "test.f03" in basenames
        assert "test.c" not in basenames
        assert "test.py" not in basenames
