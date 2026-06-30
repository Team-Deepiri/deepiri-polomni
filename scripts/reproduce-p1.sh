#!/usr/bin/env bash
# WMAP calibration P1 replication run
set -euo pipefail
cd "$(dirname "$0")/.."
poetry run polomni study run p1 --calibration
