#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="$SCRIPT_DIR/../../data/lapack"
mkdir -p "$DATA_DIR"

if [ -d "$DATA_DIR/SRC" ]; then
    echo "LAPACK already downloaded at $DATA_DIR"
    exit 0
fi

echo "Downloading LAPACK v3.12.1..."
curl -L https://github.com/Reference-LAPACK/lapack/archive/refs/tags/v3.12.1.tar.gz -o /tmp/lapack.tar.gz

echo "Extracting..."
tar -xzf /tmp/lapack.tar.gz -C /tmp

echo "Copying SRC/ and BLAS/SRC/..."
cp -r /tmp/lapack-3.12.1/SRC "$DATA_DIR/SRC"
cp -r /tmp/lapack-3.12.1/BLAS "$DATA_DIR/BLAS"

echo "Cleaning up..."
rm -rf /tmp/lapack.tar.gz /tmp/lapack-3.12.1

FILE_COUNT=$(find "$DATA_DIR" -name "*.f" -o -name "*.f90" | wc -l)
echo "Done. Found $FILE_COUNT Fortran files."
 