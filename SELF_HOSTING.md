# Self-Hosting Gitswarm

Use `gitswarm` on the `gitswarm` repo itself like this:

```bash
cd /Users/vukrosic/my-life/gitswarm
gitswarm --repo /Users/vukrosic/my-life/gitswarm
```

That runs the dashboard against the current repo, writes local state into:

- `.gitswarm/state/`
- `.agent-worktrees/`

Both paths stay local-only and are ignored by git.

