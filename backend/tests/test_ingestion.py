import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.ingestion import parse_fortran_file, extract_metadata

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
