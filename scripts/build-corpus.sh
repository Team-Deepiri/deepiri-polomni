#!/usr/bin/env bash
# Generate neural training corpus (default 500 closed-loop runs)
set -euo pipefail
cd "$(dirname "$0")/.."
COUNT="${1:-500}"
NSIDE="${NSIDE:-32}"
STEPS="${STEPS:-3}"
echo "=== Building loop corpus: ${COUNT} runs (nside=${NSIDE}, steps=${STEPS}) ==="
poetry run polomni run loop-batch --count "${COUNT}" --nside "${NSIDE}" --steps "${STEPS}" -o "data/loop_runs/batch_summary.json"
echo "=== Corpus stats ==="
poetry run polomni neural corpus
echo "=== Done — train with: bash scripts/train-neural.sh ==="
