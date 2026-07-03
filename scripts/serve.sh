#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8091}"
poetry run polomni serve --host "$HOST" --port "$PORT"
