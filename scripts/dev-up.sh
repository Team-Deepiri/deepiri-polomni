#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose -f docker/docker-compose.yml up -d polomni-lab
echo "Polomni lab: http://localhost:8091/dashboard"
