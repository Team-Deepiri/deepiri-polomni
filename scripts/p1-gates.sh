#!/usr/bin/env bash
# P1 physics gates — run before blind holdout
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Gate checks ==="
poetry run polomni study gates

echo ""
echo "=== Injection recovery (full) ==="
poetry run pytest tests/observatory/test_p1_injection_recovery.py -m slow -q

echo ""
echo "=== WMAP calibration run ==="
poetry run polomni study run p1 --calibration

echo ""
echo "=== Status ==="
poetry run polomni study status

echo ""
echo "GATES OK — ready for: polomni study run p1 --blind"
