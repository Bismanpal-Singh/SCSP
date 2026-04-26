#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ ! -d ".venv" ]]; then
  echo "Missing .venv. Create it first: python -m venv .venv"
  exit 1
fi

for port in 8000 3003; do
  if lsof -ti tcp:"$port" >/dev/null 2>&1; then
    echo "Freeing occupied port $port..."
    lsof -ti tcp:"$port" | xargs kill -9
  fi
done

cleanup() {
  [[ -n "${BACKEND_PID:-}" ]] && kill "$BACKEND_PID" 2>/dev/null || true
  [[ -n "${FRONTEND_PID:-}" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

source .venv/bin/activate
python -m uvicorn criticalmat.server:app --host localhost --port 8000 --reload --reload-dir criticalmat &
BACKEND_PID=$!

npm run dev:frontend &
FRONTEND_PID=$!

echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3003"

wait "$BACKEND_PID" "$FRONTEND_PID"
