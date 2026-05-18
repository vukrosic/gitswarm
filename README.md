# gitswarm

`gitswarm` is the standalone GitHub issues, pull requests, worktree, and agent dashboard extracted from AutoResearch-AI.

It is designed to run against any GitHub repo that has local git access and `gh` installed.

## What it does

- claims GitHub issues
- spawns agent worktrees
- reviews and merges PRs
- tracks live sessions and notifications
- keeps the operator view in a single localhost dashboard

## Quick start

```bash
cd /path/to/your/repo
npx gitswarm
```

Or install it globally:

```bash
npm install -g gitswarm
gitswarm
```

From anywhere, point it at a repo explicitly:

```bash
gitswarm --repo /path/to/your/repo
```

## Local layout

```text
gitswarm/
  bin/
  dashboard.py
  orchestrate.sh
  prompts/
```

When you launch `gitswarm` from a target repo, it writes local-only state into that repo's `.gitswarm/state/` folder and worktrees into `.agent-worktrees/`. Both are ignored by git.
