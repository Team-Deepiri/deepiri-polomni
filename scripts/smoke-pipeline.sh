#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
poetry run polomni data fetch --lite --no-gw
poetry run polomni run workflow --nside 64 --nulls 5 --no-gw
echo "PIPELINE OK"
