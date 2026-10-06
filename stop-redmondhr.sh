#!/usr/bin/env bash
# Optional emergency stop for RedmondHR (uses pid file).
# Normal UX: close the RedmondHR console window (start-redmondhr.sh EXIT trap).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${REDMONDHR_DATA_DIR:-$ROOT/data}"
PID_FILE="${REDMONDHR_PID:-$DATA_DIR/redmondhr.pid}"
PORT="${REDMONDHR_PORT:-8000}"

if [[ ! -f "$PID_FILE" ]]; then
  echo "No pid file at $PID_FILE — RedmondHR may not be running via the launcher."
  echo "If something is still listening on port $PORT, stop it manually, e.g.:"
  echo "  ss -ltnp | grep :$PORT"
  exit 0
fi

PID="$(tr -d '[:space:]' < "$PID_FILE" || true)"
if [[ -z "$PID" ]]; then
  rm -f "$PID_FILE"
  echo "Empty pid file removed."
  exit 0
fi

if ! kill -0 "$PID" 2>/dev/null; then
  rm -f "$PID_FILE"
  echo "Process $PID not running; cleaned up pid file."
  exit 0
fi

echo "Stopping RedmondHR (pid $PID)…"
kill "$PID" 2>/dev/null || true

# Wait for graceful exit
for _ in $(seq 1 20); do
  if ! kill -0 "$PID" 2>/dev/null; then
    break
  fi
  sleep 0.2
done

if kill -0 "$PID" 2>/dev/null; then
  echo "Still running; sending SIGKILL…"
  kill -9 "$PID" 2>/dev/null || true
fi

rm -f "$PID_FILE"
echo "RedmondHR stopped."
