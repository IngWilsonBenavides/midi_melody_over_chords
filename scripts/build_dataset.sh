#!/usr/bin/env bash
# build_dataset.sh — reproducible one-liner to build the full dataset.
#
# Usage:
#   bash scripts/build_dataset.sh                   # default settings
#   bash scripts/build_dataset.sh --window-bars 8   # 8-bar windows
#   bash scripts/build_dataset.sh --no-augment       # skip augmentation
#   bash scripts/build_dataset.sh --report           # generate stats report
#
# All extra arguments are forwarded to tools/dataset/build_dataset.py.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== Melodic Improviser Dataset Builder ==="
echo "Working directory: $REPO_ROOT"

# Ensure the package is importable.
if ! python -c "import tools.dataset" 2>/dev/null; then
    echo "Installing package in editable mode …"
    pip install -e ".[test]" -q
fi

python -m tools.dataset.build_dataset \
    --input-dir  data/raw \
    --output-dir data \
    --seed       42 \
    "$@"

echo ""
echo "Done. Splits written to data/splits/"
echo "Run 'bash scripts/build_dataset.sh --report' to generate the stats report."
