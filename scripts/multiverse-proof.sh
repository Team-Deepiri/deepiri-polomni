#!/usr/bin/env bash
# Full multiverse computational proof battery
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${1:-data/reports/multiverse_proof.json}"
mkdir -p "$(dirname "$OUT")"
poetry run polomni run proof -o "$OUT"
echo "=== Proof report: $OUT ==="
