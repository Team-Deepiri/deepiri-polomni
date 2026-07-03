#!/usr/bin/env bash
# Unit tests (excludes integration marker)
set -euo pipefail
cd "$(dirname "$0")/.."
poetry run python -m pytest tests/ -q -m "not integration"
