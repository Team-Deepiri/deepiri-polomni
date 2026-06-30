#!/usr/bin/env bash
# Quick multiverse proof battery (CI / pre-push smoke)
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${1:-data/reports/multiverse_proof_quick.json}"
mkdir -p "$(dirname "$OUT")"
poetry run polomni run proof --quick -o "$OUT"
echo "=== Proof report: $OUT ==="
