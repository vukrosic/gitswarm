#!/usr/bin/env bash
# dev.sh — run the gitswarm dashboard with auto-restart on code changes.
#
#   ./scripts/dev.sh [PORT]
#
# Watches Python backend files and React source/build inputs via stat(1) mtime
# polling (zero deps; works on macOS BSD stat and GNU stat). When any of them
# change, rebuilds the frontend if needed, kills the running dashboard, and
# respawns it. The browser reloads automatically when /api/agents reports a
# newer code_mtime.
#
# Ctrl-C twice to exit (once to kill the dashboard, once to break the loop).

set -u
PORT="${1:-7778}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

WATCH=(server.py github.py backend web/src web/index.html web/package.json web/tsconfig.json web/vite.config.ts shared/api-contract.md)

# Portable mtime — BSD stat (macOS) vs GNU stat.
mtimes() {
  find "${WATCH[@]}" -type f -print0 2>/dev/null |
    while IFS= read -r -d '' path; do
      stat -f "%m %N" "$path" 2>/dev/null || stat -c "%Y %n" "$path" 2>/dev/null
    done |
    sort
}

build_frontend() {
  if [ ! -d web/node_modules ]; then
    echo "[dev] web/node_modules missing — run: npm --prefix web install"
    return 1
  fi
  npm --prefix web run build >/dev/null
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
  build_frontend || exit 1
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
