#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
poetry install --with dev
poetry run python -m pytest tests/ -q -m "not integration"
poetry run polomni info
poetry run polomni data list
poetry run polomni run benchmark --nside 16
poetry run polomni math prove
echo "STACK OK"
