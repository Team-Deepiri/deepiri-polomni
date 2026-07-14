#!/usr/bin/env bash
# Polomni one-shot setup. Use --run to launch the interactive CLI lab menu.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

WITH_DEV=false
RUN=false
FETCH_DATA=false

usage() {
  cat <<'EOF'
Usage: ./setup.sh [options]

  Install Poetry deps (+ frontend npm). Pass --run to open the interactive lab menu.

Options:
  --run         After setup, run: poetry run polomni run menu
  --dev         poetry install --with dev (default: poetry install only)
  --fetch-data  polomni data fetch --lite --no-gw
  -h, --help    Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run) RUN=true; shift ;;
    --dev) WITH_DEV=true; shift ;;
    --fetch-data) FETCH_DATA=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1"; usage; exit 1 ;;
  esac
done

echo "=== Polomni setup ==="

# Git Hooks Setup
if [ -d ".git-hooks" ]; then
    git config core.hooksPath .git-hooks
    echo "Git hooks configured (core.hooksPath = .git-hooks)"
else
    echo "No .git-hooks directory found, skipping hooks setup"
fi

if ! command -v poetry >/dev/null 2>&1; then
  echo "Poetry is required: https://python-poetry.org/docs/#installation"
  exit 1
fi

if $WITH_DEV; then
  poetry install --with dev
else
  poetry install
fi

if [[ -f frontend/package.json ]] && command -v npm >/dev/null 2>&1; then
  echo "=== Frontend npm install ==="
  (cd frontend && npm install)
elif [[ -f frontend/package.json ]]; then
  echo "[warn] npm not found — skipped frontend install"
fi

mkdir -p data/reports data/loop_runs

if $FETCH_DATA; then
  echo "=== Fetch lite data catalog ==="
  poetry run polomni data fetch --lite --no-gw
fi

echo "=== Setup complete ==="
poetry run polomni info

if $RUN; then
  exec poetry run polomni run menu
fi

echo ""
echo "Next: ./setup.sh --run   or   poetry run polomni run menu"
