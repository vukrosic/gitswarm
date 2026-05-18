# Gitswarm Repo Rules

- Keep the published npm package lean and dependency-free.
- Keep `state/` and `.agent-worktrees/` local-only.
- Avoid hardcoding the source repo name; the dashboard should run against the current git checkout.
- Preserve the smallest useful workflow first.
- Prefer plain files and reproducible smoke checks over hidden state.
