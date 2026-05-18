# gitswarm API Contract

Source of truth for the `/api/*` HTTP interface. All shapes are JSON.

---

## GET /api/files

```json
{
  "files": [
    { "name": "string", "size": 12345, "mtime": 1716000000.0 }
  ]
}
```

---

## GET /api/worktrees

```json
{
  "worktrees": [
    {
      "name": "feature-xyz",
      "path": "/path/to/repo/.agent-worktrees/feature-xyz",
      "branch": "refs/heads/feature-xyz",
      "head": "abc1234",
      "commits": "abc1234",
      "ahead": 2,
      "behind": 0,
      "status": "clean",
      "dirty": false,
      "merged": false,
      "safe_remove": false,
      "running": false
    }
  ],
  "running": [
    { "issue": "42", "worktree": "feature-xyz", "active": true }
  ]
}
```

---

## GET /api/issue?num=N

```json
{
  "number": 42,
  "title": "string",
  "body": "string",
  "state": "open",
  "labels": ["area:api"],
  "assignees": ["vukrosic"],
  "created_at": "2024-05-18T12:00:00Z",
  "updated_at": "2024-05-18T12:00:00Z",
  "in_progress": false,
  "url": "https://github.com/owner/repo/issues/42"
}
```

Error: `{"error": "bad num"}` (400) or `{"error": "not found"}` (404)

---

## GET /api/pr/diff?num=N

```json
{
  "number": 42,
  "diff": "unified diff string..."
}
```

Error: `{"error": "bad num"}` (400)

---

## GET /api/agents

```json
{
  "agents": [
    {
      "id": "codex",
      "label": "codex",
      "bin": "codex",
      "model": "gpt-5.4-mini",
      "available": true
    }
  ],
  "default": "codex",
  "code_mtime": 1716000000.0
}
```

`code_mtime` is the max mtime of `server.py`, `github.py`, `backend/**/*.py`, `shared/api-contract.md`, `web/src/**`, and `web/dist/**` — used by the UI to detect when it should reload.

---

## GET /api/issues

```json
{
  "issues": [
    {
      "number": 42,
      "title": "string",
      "state": "open",
      "labels": [],
      "milestone": { "number": 7, "title": "React UI 2 - Pane parity", "state": "open" },
      "assignees": [],
      "created_at": "2024-05-18T12:00:00Z",
      "updated_at": "2024-05-18T12:00:00Z",
      "in_progress": false
    }
  ]
}
```

---

## GET /api/milestones

```json
{
  "milestones": [
    {
      "number": 7,
      "title": "React UI 2 - Pane parity",
      "description": "string",
      "state": "open",
      "open_issues": 12,
      "closed_issues": 4,
      "due_on": "2026-05-31T00:00:00Z",
      "created_at": "2026-05-01T12:00:00Z",
      "updated_at": "2026-05-17T09:00:00Z",
      "url": "https://github.com/owner/repo/milestone/7"
    }
  ]
}
```

---

## GET /api/prs

```json
{
  "prs": [
    {
      "number": 42,
      "title": "string",
      "state": "open",
      "author": "vukrosic",
      "labels": [],
      "base": "main",
      "head": "feature-xyz",
      "url": "https://github.com/owner/repo/pull/42",
      "additions": 100,
      "deletions": 50
    }
  ]
}
```

---

## GET /api/pty/list

```json
{
  "sessions": [
    {
      "sid": "a1b2c3d4e5f6",
      "label": "codex · gitswarm",
      "cwd": "/path/to/repo",
      "alive": true,
      "kind": "agent-shell"
    }
  ]
}
```

---

## GET /api/pty/stream?sid=X&offset=N&timeout=N

Binary endpoint. Response headers:

- `X-Offset`: total logical bytes available
- `X-Alive`: `"1"` if session still running, `"0"` if dead
- `X-Drop`: bytes dropped from head (buffer overflow)
- `X-Reset`: `"1"` if client should reset (buffer gap)

Response body: raw UTF-8 bytes from the PTY. Empty body = poll timeout with no new output.

Error: `{"error": "unknown sid"}` (404)

---

## GET /api/file?name=X&offset=N

```json
// raw text, Content-Type: text/plain; charset=utf-8
// Headers: X-Total-Size: 12345
```

Error: `{"error": "bad name"}` (400), `{"error": "not found"}` (404)

---

## POST /api/launch

Request:
```json
{ "issue": 42, "mode": "watch" }
```

`mode`: `"watch"` | `"headless"`

Response:
```json
{ "started": true, "sid": "a1b2c3d4e5f6", "label": "issue #42 · codex" }
```

Error: `{"error": "issue must be int"}` (400)

---

## POST /api/review

Request:
```json
{ "pr": 42 }
```

Response:
```json
{
  "started": true,
  "sid": "a1b2c3d4e5f6",
  "prompt_file": "/path/to/state/review-prompt-42.md"
}
```

---

## POST /api/merge

Request:
```json
{ "pr": 42, "strategy": "squash" }
```

`strategy`: `"squash"` | `"rebase"` | `"merge"`

Response:
```json
{ "merged": true }
```

---

## POST /api/issue/update

Request:
```json
{ "issue": 42, "title": "new title", "body": "new body" }
```

---

## POST /api/issue/create

Request:
```json
{ "title": "new issue", "body": "markdown body" }
```

---

## POST /api/issue/delete

Request:
```json
{ "issue": 42 }
```

---

## POST /api/pty/new

Request:
```json
{ "kind": "shell", "cwd": "/path/to/repo" }
```

Other kinds used by the dashboard include `agent-shell`, `agent-prompt`,
`issue-shell`, `issue-review`, `pr-review`, `merge-pr`, `ci-fix`, and
`propose-issue`.

---

## POST /api/pty/input

Request:
```json
{ "sid": "a1b2c3d4e5f6", "data": "ls\n" }
```

---

## POST /api/pty/resize

Request:
```json
{ "sid": "a1b2c3d4e5f6", "rows": 30, "cols": 120 }
```

---

## POST /api/pty/close

Request:
```json
{ "sid": "a1b2c3d4e5f6" }
```

---

## POST /api/pty/delete

Request:
```json
{ "sid": "a1b2c3d4e5f6" }
```

---

## POST /api/worktree/remove

Request:
```json
{ "name": "feature-xyz" }
```

---

## POST /api/state/cleanup

Request:
```json
{ "stale_days": 7, "dry_run": true }
```

Response:
```json
{ "updated": true }
```

---

## POST /api/issue/delete

Request:
```json
{ "issue": 42 }
```

Response:
```json
{ "deleted": true }
```

---

## POST /api/issue/create

Request:
```json
{ "title": "Issue title", "body": "Issue body" }
```

Response:
```json
{ "created": true, "number": 43 }
```

---

## POST /api/pty/new

Request:
```json
{
  "kind": "agent-shell",
  "agent": "codex",
  "cwd": ".agent-worktrees/feature-xyz",
  "rows": 30,
  "cols": 120
}
```

`kind` values: `"shell"`, `"agent-shell"`, `"pr-review"`, `"merge-pr"`, `"ci-fix"`, `"issue-shell"`, `"propose"`, `"implementer"`, `"reviewer"`

Response:
```json
{
  "sid": "a1b2c3d4e5f6",
  "label": "codex · gitswarm",
  "cwd": "/path/to/repo",
  "agent": "codex",
  "model": "gpt-5.4-mini"
}
```

---

## POST /api/pty/input

Request:
```json
{ "sid": "a1b2c3d4e5f6", "data": "ls\n" }
```

Response:
```json
{ "ok": true }
```

---

## POST /api/pty/resize

Request:
```json
{ "sid": "a1b2c3d4e5f6", "rows": 40, "cols": 140 }
```

Response:
```json
{ "ok": true }
```

---

## POST /api/pty/close

Request:
```json
{ "sid": "a1b2c3d4e5f6" }
```

Response:
```json
{ "ok": true }
```

---

## POST /api/pty/delete

Request:
```json
{ "sid": "a1b2c3d4e5f6" }
```

Response:
```json
{ "ok": true }
```

---

## POST /api/worktree/remove

Request:
```json
{ "name": "feature-xyz" }
```

Response:
```json
{ "removed": true }
```

---

## POST /api/state/cleanup

Request:
```json
{ "stale_days": 7, "dry_run": false }
```

Response:
```json
{
  "dry_run": false,
  "stale_days": 7,
  "removed": [
    { "name": "orchestrator-42.log", "size": 1234, "age_days": 10.5 }
  ],
  "kept_count": 5,
  "freed_bytes": 1234
}
```
