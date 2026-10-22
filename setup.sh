#!/usr/bin/env sh
# One-time setup on macOS / Linux: Python venv, dashboard build, desktop icon + start at login.
set -e
cd "$(dirname "$0")"

command -v python3 >/dev/null || { echo "Python 3.10+ is required"; exit 1; }
command -v npm >/dev/null || { echo "Node.js 18+ is required (https://nodejs.org/)"; exit 1; }

echo "[1/3] Installing Python packages..."
[ -d backend/.venv ] || python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install --upgrade pip >/dev/null
backend/.venv/bin/python -m pip install -r backend/requirements.txt

echo "[2/3] Building the TypeScript dashboard..."
(cd frontend && npm install --no-audit --no-fund && npm run build)

echo "[3/3] Adding desktop icon and start-at-login..."
backend/.venv/bin/python scripts/autostart.py install

echo "Done. Start it now with:  ./run.sh"
