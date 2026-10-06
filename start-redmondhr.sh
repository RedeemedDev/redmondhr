#!/usr/bin/env bash
# RedmondHR offline launcher (Linux / WSL)
# Starts uvicorn in the background, opens the default browser, then keeps
# this console in the foreground. Closing the window (or Ctrl+C) stops the
# server — same lifecycle as a normal desktop app.
#
# Windows Desktop .lnk → wsl.exe -d <distro> --cd <project> -- bash ./start-redmondhr.sh
# Use WindowStyle=1 (normal) so the console stays visible; closing it quits.
# ROOT is derived from this script's location — no reliance on caller cwd beyond --cd.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

HOST="${REDMONDHR_HOST:-127.0.0.1}"
PORT="${REDMONDHR_PORT:-8000}"
URL="http://${HOST}:${PORT}"
DATA_DIR="${REDMONDHR_DATA_DIR:-$ROOT/data}"
LOG_FILE="${REDMONDHR_LOG:-$DATA_DIR/redmondhr.log}"
PID_FILE="${REDMONDHR_PID:-$DATA_DIR/redmondhr.pid}"

mkdir -p "$DATA_DIR"

PYTHON="$ROOT/.venv/bin/python"
UVICORN="$ROOT/.venv/bin/uvicorn"

if [[ ! -x "$PYTHON" ]]; then
  cat >&2 <<MSG
RedmondHR: virtual environment not found at:
  $ROOT/.venv

One-time setup (needs internet once):
  cd "$ROOT"
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt

Then run ./start-redmondhr.sh again (no internet required after that).
MSG
  exit 1
fi

port_in_use() {
  if command -v ss >/dev/null 2>&1; then
    ss -ltn "( sport = :$PORT )" 2>/dev/null | grep -q ":$PORT"
  elif command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"$PORT" -sTCP:LISTEN -t >/dev/null 2>&1
  else
    (echo >/dev/tcp/"$HOST"/"$PORT") >/dev/null 2>&1
  fi
}

pid_alive() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

is_wsl() {
  grep -qiE 'microsoft|wsl' /proc/version 2>/dev/null
}

open_browser() {
  # When launched from a Windows Desktop icon via wsl.exe, prefer the Windows
  # default browser so Adam sees the app without a Linux GUI session.
  if is_wsl; then
    if command -v wslview >/dev/null 2>&1; then
      wslview "$URL" >/dev/null 2>&1 && return 0 || true
    fi
    local win_cmd=""
    for c in /mnt/c/Windows/System32/cmd.exe /mnt/c/WINDOWS/System32/cmd.exe; do
      if [[ -x "$c" ]]; then
        win_cmd="$c"
        break
      fi
    done
    if [[ -n "$win_cmd" ]]; then
      # Empty window title arg is required for "start".
      "$win_cmd" /c start "" "$URL" >/dev/null 2>&1 && return 0 || true
    fi
    if command -v powershell.exe >/dev/null 2>&1; then
      powershell.exe -NoProfile -Command "Start-Process '$URL'" >/dev/null 2>&1 && return 0 || true
    fi
  fi

  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 || true
  elif command -v gio >/dev/null 2>&1; then
    gio open "$URL" >/dev/null 2>&1 || true
  elif command -v sensible-browser >/dev/null 2>&1; then
    sensible-browser "$URL" >/dev/null 2>&1 || true
  else
    echo "Open your browser to: $URL"
  fi
}

# Stop uvicorn via pid file (same logic as stop-redmondhr.sh).
# Called from EXIT/INT/TERM/HUP so closing the console window quits the app.
stop_server() {
  local pid=""
  if [[ -f "$PID_FILE" ]]; then
    pid="$(tr -d '[:space:]' < "$PID_FILE" || true)"
  fi
  if [[ -z "$pid" ]]; then
    rm -f "$PID_FILE"
    return 0
  fi
  if ! pid_alive "$pid"; then
    rm -f "$PID_FILE"
    return 0
  fi
  echo "Stopping RedmondHR (pid $pid)…"
  kill "$pid" 2>/dev/null || true
  local _
  for _ in $(seq 1 20); do
    if ! pid_alive "$pid"; then
      break
    fi
    sleep 0.2
  done
  if pid_alive "$pid"; then
    echo "Still running; sending SIGKILL…"
    kill -9 "$pid" 2>/dev/null || true
  fi
  rm -f "$PID_FILE"
  echo "RedmondHR stopped."
}

cleanup() {
  # Clear traps first so EXIT does not re-enter after signal handlers call exit.
  trap - EXIT INT TERM HUP
  stop_server
}

WAIT_PID=""

# --- Already running: open browser and take ownership of this console ---
if [[ -f "$PID_FILE" ]]; then
  OLD_PID="$(tr -d '[:space:]' < "$PID_FILE" || true)"
  if pid_alive "$OLD_PID"; then
    echo "RedmondHR already running (pid $OLD_PID). Opening browser…"
    open_browser
    WAIT_PID="$OLD_PID"
    trap cleanup EXIT
    trap 'cleanup; exit 0' INT TERM HUP
    echo ""
    echo "RedmondHR is running at $URL"
    echo "Close this window to stop RedmondHR."
    echo "(Ctrl+C also stops.)"
    echo ""
    while pid_alive "$WAIT_PID"; do
      sleep 1
    done
    exit 0
  fi
  rm -f "$PID_FILE"
fi

if port_in_use; then
  echo "Port $PORT already in use — assuming RedmondHR is up. Opening browser…"
  open_browser
  # Best-effort: discover listener pid so this console can still stop it.
  DISCOVERED=""
  if command -v lsof >/dev/null 2>&1; then
    DISCOVERED="$(lsof -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null | head -n1 || true)"
  elif command -v ss >/dev/null 2>&1; then
    DISCOVERED="$(ss -ltnp "( sport = :$PORT )" 2>/dev/null | grep -oE 'pid=[0-9]+' | head -n1 | cut -d= -f2 || true)"
  fi
  if [[ -n "$DISCOVERED" ]] && pid_alive "$DISCOVERED"; then
    echo "$DISCOVERED" > "$PID_FILE"
    WAIT_PID="$DISCOVERED"
    trap cleanup EXIT
    trap 'cleanup; exit 0' INT TERM HUP
    echo ""
    echo "RedmondHR is running at $URL (pid $DISCOVERED)"
    echo "Close this window to stop RedmondHR."
    echo "(Ctrl+C also stops.)"
    echo ""
    while pid_alive "$WAIT_PID"; do
      sleep 1
    done
    exit 0
  fi
  echo "Could not find a pid for port $PORT — close this window will NOT stop the server."
  echo "Optional emergency stop: ./stop-redmondhr.sh"
  echo ""
  # Keep a visible console so the user knows something is up; no cleanup ownership.
  echo "Press Ctrl+C or close this window to dismiss."
  while true; do sleep 3600; done
fi

{
  echo "===== $(date '+%Y-%m-%d %H:%M:%S %Z') starting RedmondHR ====="
  echo "ROOT=$ROOT HOST=$HOST PORT=$PORT"
} >> "$LOG_FILE"

export PYTHONUNBUFFERED=1
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

# Background child (not nohup/disown): same session so closing the console
# can deliver SIGHUP; EXIT trap also kills via pid file.
if [[ -x "$UVICORN" ]]; then
  "$UVICORN" app.main:app --host "$HOST" --port "$PORT" \
    >> "$LOG_FILE" 2>&1 &
else
  "$PYTHON" -m uvicorn app.main:app --host "$HOST" --port "$PORT" \
    >> "$LOG_FILE" 2>&1 &
fi
NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"
WAIT_PID="$NEW_PID"

trap cleanup EXIT
trap 'cleanup; exit 0' INT TERM HUP

for _ in $(seq 1 20); do
  if port_in_use; then
    break
  fi
  if ! pid_alive "$NEW_PID"; then
    echo "RedmondHR failed to start. Check log: $LOG_FILE" >&2
    rm -f "$PID_FILE"
    trap - EXIT INT TERM HUP
    exit 1
  fi
  sleep 0.25
done

if port_in_use; then
  echo "RedmondHR started (pid $NEW_PID) at $URL"
else
  echo "RedmondHR started (pid $NEW_PID) but port $PORT not listening yet."
  echo "Check log: $LOG_FILE"
fi

open_browser

echo ""
echo "RedmondHR is running at $URL"
echo "Close this window to stop RedmondHR."
echo "(Ctrl+C also stops.)"
echo ""

# Foreground wait: when uvicorn exits, we exit and the trap cleans up.
wait "$NEW_PID" || true
