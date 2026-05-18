# Gitswarm Repo Rules

- Keep the published npm package lean and dependency-free.
- Keep `state/` and `.agent-worktrees/` local-only.
- Avoid hardcoding the source repo name; the dashboard should run against the current git checkout.
- Preserve the smallest useful workflow first.
- Prefer plain files and reproducible smoke checks over hidden state.

## Dashboard dev workflow

The dashboard is a long-running Python process that serves the built React app
from `web/dist/`. After editing `server.py`, `github.py`, `backend/*.py`, or
React files under `web/src/`, restart the dashboard so the backend and built
frontend are both current.

1. Restart the dashboard. Prefer `./scripts/dev.sh [PORT]` (the watcher
   rebuilds React and respawns the server on every save). If the user is running
   `python3 server.py` / `python3 dashboard.py` directly, kill that PID
   and start it again on the same port.
2. The browser will reload itself — the React app polls `/api/agents`
   every 4s and calls `location.reload()` when `code_mtime` bumps. Do not tell the
   user to refresh manually.

If you edit the code and leave the old server running, the user sees
nothing change. Always restart.
