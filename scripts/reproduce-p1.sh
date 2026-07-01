#!/usr/bin/env bash
# Full P1 replication package — Gates 1–4, calibration, blind holdout, artifact hash.
set -euo pipefail
cd "$(dirname "$0")/.."

OUT_DIR="${POLOMNI_REPRO_OUT:-data/studies/p1_holdout/replication}"
mkdir -p "$OUT_DIR"

echo "=== P1 Replication Package ==="
echo "Output: $OUT_DIR"
echo "Git: $(git rev-parse HEAD 2>/dev/null || echo unknown)"
date -u +"%Y-%m-%dT%H:%M:%SZ" | tee "$OUT_DIR/timestamp.txt"

echo ""
echo "=== 0. Dependencies ==="
poetry install --with dev --no-ansi

echo ""
echo "=== 1. Fetch public data (lite + maps if missing) ==="
poetry run polomni data fetch --wmap --planck 2>/dev/null || poetry run polomni data fetch

echo ""
echo "=== 2. Gates 1–3 + injection recovery + WMAP calibration ==="
bash scripts/p1-gates.sh 2>&1 | tee "$OUT_DIR/gates_calibration.log"

echo ""
echo "=== 3. Gate 4 — blind Planck SMICA holdout ==="
poetry run polomni study run p1 --blind --json | tee "$OUT_DIR/holdout_blind.json"

echo ""
echo "=== 4. Study status ==="
poetry run polomni study status | tee "$OUT_DIR/status.txt"

echo ""
echo "=== 5. Artifact manifest ==="
{
  echo "git_sha=$(git rev-parse HEAD 2>/dev/null || echo unknown)"
  echo "study_config_sha256=$(sha256sum data/studies/p1_holdout/study_config.json | awk '{print $1}')"
  echo "prereg_sha256=$(sha256sum docs/studies/P1_CMB_RADON_SCAR_PREREG.md | awk '{print $1}')"
  if [[ -f data/studies/p1_holdout/RESULT.json ]]; then
    echo "result_sha256=$(sha256sum data/studies/p1_holdout/RESULT.json | awk '{print $1}')"
  fi
  if [[ -f data/cache/manifest.json ]]; then
    echo "cache_manifest_sha256=$(sha256sum data/cache/manifest.json | awk '{print $1}')"
  fi
} | tee "$OUT_DIR/manifest.sha256"

echo ""
echo "=== 6. Gate 5 — independent replication verify ==="
poetry run polomni study replicate --json | tee "$OUT_DIR/gate5_verify.json"

echo ""
echo "=== REPLICATION COMPLETE ==="
echo "Results: data/studies/p1_holdout/RESULT.json"
echo "Logs: $OUT_DIR/"
