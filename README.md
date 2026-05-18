![GitSwarm hero](./assets/gitswarm-hero.png)

# gitswarm

`gitswarm` is a standalone GitHub issues, pull requests, worktree, and agent dashboard for automated AI development.

It is designed to run against any GitHub repo that has local git access and `gh` installed.

> This project is usable, but it still has bugs and unfinished features. If you want a more stable version, wait about a week. If you want to dogfood it on your own repo today, Codex can help you solve issues and keep moving. You can also ask Codex to take inspiration from this and adapt the ideas into your own system.

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

Set up repo defaults first:

```bash
gitswarm init --repo /path/to/your/repo
gitswarm doctor --repo /path/to/your/repo
```

For dogfooding `gitswarm` on its own repo, read [SELF_HOSTING.md](./SELF_HOSTING.md).

## Local layout

```text
gitswarm/
  bin/
  backend/
  dashboard.py
  server.py
  github.py
  web/dist/
  orchestrate.sh
  SELF_HOSTING.md
  prompts/
```

When you launch `gitswarm` from a target repo, it writes local-only state into that repo's `.gitswarm/state/` folder and worktrees into `.agent-worktrees/`. Both are ignored by git.
