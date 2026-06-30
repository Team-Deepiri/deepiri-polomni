#!/usr/bin/env bash
# Train axis + branch predictors from loop corpus
set -euo pipefail
cd "$(dirname "$0")/.."
EPOCHS="${1:-100}"
poetry run polomni neural train --epochs "$EPOCHS"
