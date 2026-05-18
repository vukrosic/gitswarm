#!/usr/bin/env bash
# dev.sh — run the gitswarm dashboard with auto-restart on code changes.
#
#   ./scripts/dev.sh [PORT]
#
# Watches ui.py, server.py, github.py via stat(1) mtime polling (zero deps;
# works on macOS BSD stat and GNU stat). When any of them change, kills the
# running dashboard and respawns it. The browser then picks up the new build
# automatically because ui.py polls /api/agents.code_mtime and reloads on
# change.
#
# Ctrl-C twice to exit (once to kill the dashboard, once to break the loop).

set -u
PORT="${1:-7778}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

WATCH=(ui.py server.py github.py)

# Portable mtime — BSD stat (macOS) vs GNU stat.
mtimes() {
  if stat -f %m "${WATCH[@]}" 2>/dev/null; then return; fi
  stat -c %Y "${WATCH[@]}" 2>/dev/null
}

cleanup() {
  if [ -n "${PID:-}" ] && kill -0 "$PID" 2>/dev/null; then
    kill "$PID" 2>/dev/null
    wait "$PID" 2>/dev/null
  fi
}
trap cleanup EXIT INT TERM

echo "[dev] gitswarm dashboard on :$PORT — watching ${WATCH[*]}"
while true; do
  python3 server.py "$PORT" &
  PID=$!
  BEFORE="$(mtimes | tr '\n' ' ')"
  while sleep 1; do
    if ! kill -0 "$PID" 2>/dev/null; then
      echo "[dev] dashboard exited (pid $PID); restarting in 1s"
      sleep 1
      break
    fi
    NOW="$(mtimes | tr '\n' ' ')"
    if [ "$NOW" != "$BEFORE" ]; then
      echo "[dev] code changed — restarting"
      kill "$PID" 2>/dev/null
      wait "$PID" 2>/dev/null
      break
    fi
  done
done
