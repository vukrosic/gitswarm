#!/usr/bin/env python3
"""Tiny zero-dep web dashboard for gitswarm.

Browser-friendly tail -f over every file in state/, plus a quick view of
worktrees and recent commits. Run with:

    python3 dashboard.py [PORT]

Opens at http://localhost:7777 by default. Localhost-only, no auth.
"""
import fcntl
import http.server
import json
import os
import pty
import re
import secrets
import select
import shlex
import signal
import struct
import subprocess
import sys
import termios
import threading
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = Path.cwd().resolve()
REPO_NAME = REPO_ROOT.name
STATE_DIR = REPO_ROOT / ".gitswarm" / "state"
WORKTREES_DIR = REPO_ROOT / ".agent-worktrees"
PROMPTS_DIR = PACKAGE_ROOT / "prompts"
USER_SHELL = os.environ.get("SHELL", "/bin/bash")

# Defaults for the per-issue interactive launcher. The "yolo" flag bypasses
# codex's approval prompts and sandbox — only safe because each agent runs in
# its own disposable worktree.
CODEX_BIN   = os.environ.get("CODEX_BIN", "codex")
CODEX_MODEL = os.environ.get("CODEX_MODEL", "gpt-5.4-mini")
CODEX_YOLO  = os.environ.get("CODEX_YOLO", "--dangerously-bypass-approvals-and-sandbox")

# Agent registry. Each entry knows how to build a one-shot interactive
# invocation: `<bin> <yolo> [<model_flag> <model>] [--] "<prompt>"`. Adding a
# new agent is a matter of dropping another dict in here.
#
# prompt_style:
#   "double-dash" — `bin flags -m model -- "prompt"` (codex)
#   "positional"  — `bin flags "prompt"` (claude, claude-minimax-free)
AGENTS = {
    "codex": {
        "label": "codex",
        "bin": os.environ.get("CODEX_BIN", "codex"),
        "yolo": os.environ.get("CODEX_YOLO", "--dangerously-bypass-approvals-and-sandbox"),
        "model": os.environ.get("CODEX_MODEL", "gpt-5.4-mini"),
        "model_flag": "-m",
        "prompt_style": "double-dash",
    },
    "claude": {
        "label": "claude",
        "bin": os.environ.get("CLAUDE_BIN", "claude"),
        "yolo": os.environ.get("CLAUDE_YOLO", "--dangerously-skip-permissions"),
        "model": os.environ.get("CLAUDE_MODEL", ""),  # empty → claude's default
        "model_flag": "--model",
        "prompt_style": "positional",
    },
    "claude-minimax-free": {
        "label": "minimax (cmf)",
        "bin": os.environ.get("CMF_BIN", "claude-minimax-free"),
        "yolo": "",                # the cmf wrapper already adds --dangerously-skip-permissions
        "model": "",               # cmf wrapper pins the model via env vars
        "model_flag": "",
        "prompt_style": "positional",
    },
}
DEFAULT_AGENT = os.environ.get("GITSWARM_AGENT", "codex")


def resolve_agent(agent_id, override_model=None, override_bin=None, override_yolo=None):
    """Look up an agent preset; allow per-call overrides for bin/model/yolo."""
    a = dict(AGENTS.get(agent_id) or AGENTS[DEFAULT_AGENT])
    if override_bin:   a["bin"]   = override_bin
    if override_model: a["model"] = override_model
    if override_yolo is not None: a["yolo"] = override_yolo
    a.setdefault("id", agent_id if agent_id in AGENTS else DEFAULT_AGENT)
    return a


def build_agent_cmd(agent, prompt_expr):
    """Build the shell command that runs <agent> with <prompt_expr> as the prompt.

    prompt_expr is the un-quoted text that produces the prompt at runtime
    inside the bash wrapper, e.g. ``$(cat /path/to/prompt)`` or
    ``$(cat "$PROMPT_FILE")``. We wrap it in double quotes here so the entire
    expansion is one argv element.
    """
    parts = [shlex.quote(agent["bin"])]
    if agent.get("yolo"):
        parts.append(agent["yolo"])
    if agent.get("model_flag") and agent.get("model"):
        parts.extend([agent["model_flag"], shlex.quote(agent["model"])])
    if agent.get("prompt_style") == "double-dash":
        parts.append("--")
    parts.append(f'"{prompt_expr}"')
    return " ".join(parts)


def agent_short(agent):
    """Short label for the banner line in the PTY wrapper."""
    if not agent.get("yolo"):
        return agent["id"]
    return "yolo" if ("bypass" in agent["yolo"] or "yolo" in agent["yolo"]) else agent["id"]

def list_state_files():
    if not STATE_DIR.exists():
        return []
    out = []
    for p in sorted(STATE_DIR.iterdir(), key=lambda x: -x.stat().st_mtime):
        if p.name.startswith(".") or p.is_dir():
            continue
        st = p.stat()
        out.append({"name": p.name, "size": st.st_size, "mtime": st.st_mtime})
    return out


# ---------- PTY session manager ----------
# Spawns child processes under a real pseudo-terminal so the browser xterm can
# write keystrokes back to them. Output is buffered in memory; clients long-poll
# /api/pty/stream with a byte offset.

_PTY_SESSIONS = {}   # sid -> session dict
_PTY_LOCK = threading.Lock()
_PTY_BUF_CAP = 4 * 1024 * 1024  # 4MB per session; older bytes get trimmed


def _set_winsize(fd, rows, cols):
    try:
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
    except OSError:
        pass


def spawn_pty(argv, cwd=None, env_extra=None, label="", rows=30, cols=120):
    """Fork a child under a PTY, return the session dict. Output is collected
    in sess['buf']; sess['drop'] counts how many bytes were trimmed from the
    head so clients can detect missed data and reset."""
    if isinstance(argv, str):
        argv = shlex.split(argv)
    sid = secrets.token_hex(6)
    pid, fd = pty.fork()
    if pid == 0:
        try:
            if cwd:
                os.chdir(cwd)
            env = os.environ.copy()
            # Force a real terminal type for children. The dashboard itself is
            # often launched from a non-interactive shell, which can leave TERM
            # stuck at "dumb" and makes Codex refuse to start its TUI.
            env["TERM"] = "xterm-256color"
            env["COLORTERM"] = "truecolor"
            if env_extra:
                env.update(env_extra)
            for k, v in env.items():
                os.environ[k] = v
            os.execvp(argv[0], argv)
        except Exception as e:
            os.write(2, f"\r\nexec failed: {e}\r\n".encode())
            os._exit(127)
    _set_winsize(fd, rows, cols)
    sess = {
        "sid": sid,
        "fd": fd,
        "pid": pid,
        "argv": argv,
        "cwd": cwd or os.getcwd(),
        "label": label or " ".join(argv),
        "started": time.time(),
        "last_output": time.time(),
        "last_input": time.time(),
        "rows": rows, "cols": cols,
        "buf": bytearray(),
        "drop": 0,                       # bytes trimmed off the front
        "cond": threading.Condition(),
        "alive": True,
        "exit_status": None,
    }
    with _PTY_LOCK:
        _PTY_SESSIONS[sid] = sess
    threading.Thread(target=_pty_reader, args=(sid,), daemon=True).start()
    threading.Thread(target=_pty_waiter, args=(sid,), daemon=True).start()
    return sess


def _pty_reader(sid):
    sess = _PTY_SESSIONS.get(sid)
    if not sess:
        return
    fd = sess["fd"]
    try:
        while True:
            try:
                r, _, _ = select.select([fd], [], [], 1.0)
            except (ValueError, OSError):
                break
            if fd in r:
                try:
                    chunk = os.read(fd, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                with sess["cond"]:
                    sess["last_output"] = time.time()
                    sess["buf"].extend(chunk)
                    # Ring-buffer cap: trim oldest bytes if we exceed cap.
                    excess = len(sess["buf"]) - _PTY_BUF_CAP
                    if excess > 0:
                        del sess["buf"][:excess]
                        sess["drop"] += excess
                    sess["cond"].notify_all()
            if not sess["alive"]:
                break
    finally:
        sess["alive"] = False
        with sess["cond"]:
            sess["cond"].notify_all()


def _pty_waiter(sid):
    sess = _PTY_SESSIONS.get(sid)
    if not sess:
        return
    try:
        _, status = os.waitpid(sess["pid"], 0)
        sess["exit_status"] = status
    except OSError:
        pass
    sess["alive"] = False
    try:
        os.close(sess["fd"])
    except OSError:
        pass
    with sess["cond"]:
        sess["cond"].notify_all()


def pty_write(sid, data: bytes) -> bool:
    sess = _PTY_SESSIONS.get(sid)
    if not sess or not sess["alive"]:
        return False
    try:
        os.write(sess["fd"], data)
        sess["last_input"] = time.time()
        return True
    except OSError:
        return False


def pty_resize(sid, rows, cols):
    sess = _PTY_SESSIONS.get(sid)
    if not sess:
        return False
    _set_winsize(sess["fd"], rows, cols)
    sess["rows"], sess["cols"] = rows, cols
    return True


def pty_read(sid, offset, timeout=20):
    """Long-poll. Returns (data_bytes, new_logical_offset, alive, drop).

    The "logical offset" is total bytes ever written (including trimmed).
    drop is the count of bytes trimmed off the front so far; if the client's
    offset is below drop, the client must reset (buffer hole)."""
    sess = _PTY_SESSIONS.get(sid)
    if not sess:
        return None
    deadline = time.time() + timeout
    with sess["cond"]:
        while True:
            drop = sess["drop"]
            logical_len = drop + len(sess["buf"])
            if offset < drop:
                # Client missed bytes; send whatever's in the buffer and bump them up.
                data = bytes(sess["buf"])
                return data, logical_len, sess["alive"], drop, True
            buf_off = offset - drop
            if buf_off < len(sess["buf"]):
                data = bytes(sess["buf"][buf_off:])
                return data, logical_len, sess["alive"], drop, False
            if not sess["alive"]:
                return b"", logical_len, False, drop, False
            remaining = deadline - time.time()
            if remaining <= 0:
                return b"", logical_len, sess["alive"], drop, False
            sess["cond"].wait(timeout=min(remaining, 5))


def kill_pty(sid):
    sess = _PTY_SESSIONS.get(sid)
    if not sess:
        return False
    try:
        os.killpg(os.getpgid(sess["pid"]), signal.SIGHUP)
    except Exception:
        try:
            os.kill(sess["pid"], signal.SIGHUP)
        except OSError:
            pass
    sess["alive"] = False
    return True


def list_ptys():
    with _PTY_LOCK:
        return [
            {
                "sid": s["sid"],
                "label": s["label"],
                "cwd": s["cwd"],
                "alive": s["alive"],
                "started": s["started"],
                "last_output": s.get("last_output") or s["started"],
                "last_input": s.get("last_input") or s["started"],
                "rows": s["rows"], "cols": s["cols"],
            }
            for s in _PTY_SESSIONS.values()
        ]


def reap_dead_ptys(max_age_dead=600):
    """Drop dead sessions older than max_age_dead seconds so they stop cluttering the list."""
    now = time.time()
    with _PTY_LOCK:
        dead = [sid for sid, s in _PTY_SESSIONS.items()
                if not s["alive"] and (now - s["started"]) > max_age_dead]
        for sid in dead:
            _PTY_SESSIONS.pop(sid, None)


def _safe_relpath(p: Path) -> str:
    try:
        return str(p.relative_to(REPO_ROOT))
    except ValueError:
        return str(p)


def spawn_shell_session(cwd: Path, label: str = "", env_extra=None):
    """Spawn a login-ish interactive shell under a PTY."""
    if not cwd.exists():
        return {"error": f"cwd does not exist: {cwd}"}
    # -i ensures bash/zsh load rc files and run interactively.
    argv = [USER_SHELL, "-i"]
    sess = spawn_pty(argv, cwd=str(cwd), env_extra=env_extra,
                     label=label or f"shell · {_safe_relpath(cwd)}")
    return {"sid": sess["sid"], "label": sess["label"], "cwd": sess["cwd"]}


def _text_preview(text, limit=180):
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return ""
    blocks = [b.strip() for b in re.split(r"\n{2,}", text) if b.strip()]
    snippet = blocks[0] if blocks else text.splitlines()[0]
    snippet = re.sub(r"\s+", " ", snippet)
    if len(snippet) > limit:
        snippet = snippet[: max(0, limit - 1)].rstrip() + "…"
    return snippet


def _issue_label_suggestions(title, body):
    hay = f"{title}\n{body}".lower()
    suggestions = []
    rules = [
        ("needs-validation", [r"\bmaybe\b", r"\bshould we\b", r"\bidea\b", r"\bexplore\b", r"\bquestion\b"]),
        ("agent-friendly", [r"\bagent\b", r"\bdashboard\b", r"\bterminal\b", r"\bworktree\b", r"\bpty\b"]),
        ("claim-next", [r"\bimplement\b", r"\bfix\b", r"\badd\b", r"\bbuild\b", r"\bship\b"]),
        ("good first issue", [r"\bsmall\b", r"\bbeginner\b", r"\bintro\b", r"\beasy\b"]),
    ]
    for label, pats in rules:
        if any(re.search(pat, hay) for pat in pats):
            suggestions.append(label)
    return suggestions[:3]


def _git_branch_merged(branch: str) -> bool:
    if not branch:
        return False
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "branch", "--merged", "origin/main", "--format", "%(refname:short)"],
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout.splitlines()
        return branch in {line.strip() for line in out if line.strip()}
    except Exception:
        return False


def _worktree_status(path: Path):
    branch = ""
    head = ""
    dirty = False
    ahead = 0
    try:
        branch = subprocess.run(
            ["git", "-C", str(path), "branch", "--show-current"],
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout.strip()
    except Exception:
        branch = ""
    try:
        head = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout.strip()
    except Exception:
        head = ""
    try:
        dirty = bool(subprocess.run(
            ["git", "-C", str(path), "status", "--porcelain"],
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout.strip())
    except Exception:
        dirty = False
    try:
        commits = subprocess.run(
            ["git", "-C", str(path), "log", "--oneline", "origin/main..HEAD"],
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout.strip()
        ahead = len([line for line in commits.splitlines() if line.strip()])
    except Exception:
        ahead = 0
    merged = _git_branch_merged(branch)
    if dirty:
        status = "dirty"
    elif merged:
        status = "merged"
    elif ahead:
        status = "merge candidate"
    else:
        status = "clean"
    return {
        "branch": branch,
        "head": head,
        "dirty": dirty,
        "ahead": ahead,
        "merged": merged,
        "status": status,
        "safe_remove": merged and not dirty,
    }


def _pty_in_use(worktree_path: Path) -> bool:
    prefix = str(worktree_path)
    with _PTY_LOCK:
        for sess in _PTY_SESSIONS.values():
            cwd = sess.get("cwd") or ""
            if cwd == prefix or cwd.startswith(prefix + os.sep):
                return True
    return False


def git_branch_exists(branch: str) -> bool:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        timeout=5,
    ).returncode == 0


def git_worktree_for_branch(branch: str):
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "worktree", "list", "--porcelain"],
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout
    except Exception:
        return None
    current = None
    target = f"refs/heads/{branch}"
    for line in out.splitlines():
        if line.startswith("worktree "):
            current = Path(line.split(" ", 1)[1])
        elif current and line == f"branch {target}":
            return current
    return None


def prepare_issue_worktree(issue_num: int):
    """Run the orchestrator's worktree-setup steps up to (but not including)
    spawning the agent. Returns paths so the caller can drop a shell into the
    worktree with the prompt file ready to use.

    We do the minimum here: fetch the issue title, create the branch + worktree,
    relabel the issue, and materialise the prompt file. The full orchestrator
    pipeline (codex/claude exec, PR creation, reviewer) is skipped because the
    user is taking interactive control.
    """
    if not (1 <= issue_num <= 9999):
        return {"error": "bad issue number"}
    # Title -> slug -> branch name (mirror orchestrate.sh's slug_for_issue).
    try:
        issue_meta = fetch_issue_meta(issue_num)
        title = (issue_meta.get("title") or "").strip()
    except Exception as e:
        return {"error": f"gh api issue #{issue_num}: {gh_error(e)}"}
    if not title:
        return {"error": f"could not fetch title for issue #{issue_num}"}
    slug = re.sub(r"^\[(agent|goal)\][^a-zA-Z0-9]*", "", title)
    slug = re.sub(r"^G[0-9]+[^a-zA-Z0-9]*", "", slug)
    slug = re.sub(r"—.*$", "", slug)
    slug = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-")[:40]
    branch = f"agent/{issue_num}-{slug}"
    worktree = WORKTREES_DIR / f"{issue_num}-{slug}"

    WORKTREES_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["git", "-C", str(REPO_ROOT), "worktree", "prune"],
            capture_output=True, text=True, timeout=15,
        )
    except Exception:
        pass

    reused = False
    existing_for_branch = git_worktree_for_branch(branch)
    if existing_for_branch and existing_for_branch.exists():
        worktree = existing_for_branch
        reused = True
    elif worktree.exists():
        reused = True
    else:
        if git_branch_exists(branch):
            cmd = ["git", "-C", str(REPO_ROOT), "worktree", "add", str(worktree), branch]
        else:
            cmd = ["git", "-C", str(REPO_ROOT), "worktree", "add", "-b", branch,
                   str(worktree), "origin/main"]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=30)
        except subprocess.CalledProcessError as e:
            return {"error": f"git worktree add: {(e.stderr or e.stdout or '').strip()}"}

    # Relabel issue (best effort).
    try:
        subprocess.run(
            ["gh", "issue", "edit", str(issue_num),
             "--add-label", "in-progress", "--remove-label", "claim-next"],
            capture_output=True, text=True, timeout=15,
        )
    except Exception:
        pass

    # Materialise the prompt file via the same template the orchestrator uses.
    template_path = PROMPTS_DIR / "implement.md"
    body_path = STATE_DIR / f"issue-{issue_num}.body.md"
    prompt_path = STATE_DIR / f"prompt-{issue_num}.md"
    try:
        body = issue_meta.get("body") or fetch_issue_body(str(issue_num))
        body_path.write_text(body)
        if template_path.exists():
            tpl = template_path.read_text()
            prompt_path.write_text(
                tpl.replace("$ISSUE_BODY", body)
                   .replace("$BRANCH", branch)
                   .replace("$WORKTREE", str(worktree))
                   .replace("$ISSUE_NUMBER", str(issue_num))
                   .replace("$REPO_NAME", REPO_NAME)
            )
    except Exception as e:
        return {
            "warning": f"worktree created but prompt prep failed: {e}",
            "branch": branch, "worktree": str(worktree),
        }
    invalidate_caches()
    return {
        "created": not reused,
        "reused": reused,
        "branch": branch,
        "worktree": str(worktree),
        "prompt_file": str(prompt_path),
    }


# Simple in-memory caches so panels don't hammer the gh API.
_ISSUES_CACHE = {"ts": 0, "data": None}
_PRS_CACHE = {"ts": 0, "data": None}


def gh_error(exc):
    if isinstance(exc, subprocess.CalledProcessError):
        msg = (exc.stderr or exc.output or "").strip()
        return msg or str(exc)
    if isinstance(exc, subprocess.TimeoutExpired):
        return f"timed out after {exc.timeout}s"
    return str(exc)


def is_transient_gh_error(msg):
    low = (msg or "").lower()
    return any(term in low for term in (
        "eof", "timed out", "timeout", "connection reset",
        "tls handshake", "502", "503", "504",
    ))


def run_gh(args, timeout=20, retries=2):
    """Run gh with small retries for network EOFs, preserving final stderr."""
    last = None
    for attempt in range(retries + 1):
        try:
            result = subprocess.run(
                ["gh", *args],
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired as e:
            last = e
            if attempt < retries:
                time.sleep(0.4 * (attempt + 1))
                continue
            raise
        if result.returncode == 0:
            return result.stdout
        last = subprocess.CalledProcessError(
            result.returncode, ["gh", *args], output=result.stdout, stderr=result.stderr
        )
        if attempt >= retries or not is_transient_gh_error(gh_error(last)):
            raise last
        time.sleep(0.4 * (attempt + 1))
    raise last


def github_repo_slug():
    remote = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "remote", "get-url", "origin"],
        capture_output=True, text=True, timeout=5, check=True,
    ).stdout.strip()
    m = re.search(r"github\.com[:/]([^/]+)/(.+?)(?:\.git)?$", remote.rstrip("/"))
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    return run_gh(["repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"], timeout=10).strip()


def gh_api_json(path, timeout=20, retries=2):
    return json.loads(run_gh(["api", path], timeout=timeout, retries=retries))


def gh_api_text(path, headers=None, timeout=20, retries=2):
    args = ["api"]
    for header in headers or []:
        args.extend(["-H", header])
    args.append(path)
    return run_gh(args, timeout=timeout, retries=retries)


def fetch_pr_meta(pr_num: int):
    slug = github_repo_slug()
    raw = gh_api_json(f"repos/{slug}/pulls/{pr_num}", timeout=20, retries=2)
    meta = {
        "number": raw.get("number"),
        "title": raw.get("title") or "",
        "body": raw.get("body") or "",
        "url": raw.get("html_url"),
        "headRefName": (raw.get("head") or {}).get("ref") or "",
        "isDraft": bool(raw.get("draft")),
        "mergeable": raw.get("mergeable"),
        "state": raw.get("state"),
        "mergedAt": raw.get("merged_at"),
        "reviewDecision": "",
    }
    try:
        reviews = gh_api_json(f"repos/{slug}/pulls/{pr_num}/reviews", timeout=20, retries=1)
        latest_by_user = {}
        for review in reviews if isinstance(reviews, list) else []:
            user = ((review.get("user") or {}).get("login") or str(review.get("user") or ""))
            state = (review.get("state") or "").upper()
            if user and state in {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}:
                latest_by_user[user] = state
        states = set(latest_by_user.values())
        if "CHANGES_REQUESTED" in states:
            meta["reviewDecision"] = "CHANGES_REQUESTED"
        elif "APPROVED" in states:
            meta["reviewDecision"] = "APPROVED"
    except Exception:
        pass
    return meta


def fetch_issue_meta(issue_num):
    slug = github_repo_slug()
    raw = gh_api_json(f"repos/{slug}/issues/{issue_num}", timeout=15, retries=2)
    return {
        "body": raw.get("body") or "",
        "title": raw.get("title") or "",
        "url": raw.get("html_url") or "",
        "labels": [
            label.get("name")
            for label in raw.get("labels", [])
            if isinstance(label, dict) and label.get("name")
        ],
    }


def fetch_issue_body(issue_num: str):
    return fetch_issue_meta(issue_num).get("body") or ""


def fetch_pr_diff(pr_num: int):
    slug = github_repo_slug()
    path = f"repos/{slug}/pulls/{pr_num}"
    try:
        return gh_api_text(
            path,
            headers=["Accept: application/vnd.github.v3.diff"],
            timeout=30,
            retries=2,
        )
    except Exception as rest_err:
        try:
            return run_gh(["pr", "diff", str(pr_num)], timeout=30, retries=1)
        except Exception as diff_err:
            raise RuntimeError(f"REST diff failed: {gh_error(rest_err)}; gh pr diff failed: {gh_error(diff_err)}")


def list_issues():
    if _ISSUES_CACHE["data"] and time.time() - _ISSUES_CACHE["ts"] < 20:
        return _ISSUES_CACHE["data"]
    try:
        out = subprocess.run(
            ["gh", "issue", "list", "--state", "open",
             "--limit", "100", "--json", "number,title,body,labels,url,author,assignees,comments,createdAt,updatedAt,state"],
            capture_output=True, text=True, timeout=20, check=True,
        ).stdout
        issues = json.loads(out)
        for it in issues:
            it["labels"] = [l["name"] for l in it.get("labels", [])]
            it["assignees"] = [a.get("login") for a in it.get("assignees", []) if a.get("login")]
            it["in_progress"] = "in-progress" in it["labels"]
            it["claim_next"] = "claim-next" in it["labels"]
            it["parked"] = "needs-validation" in it["labels"]
            it["body"] = it.get("body") or ""
            it["summary"] = _text_preview(it["body"], 180) or "no body yet"
            it["suggested_labels"] = _issue_label_suggestions(it.get("title") or "", it["body"])
            author = it.get("author") or {}
            it["author"] = author.get("login") if isinstance(author, dict) else ""
            it["comment_count"] = it.get("comments") or 0
        _ISSUES_CACHE.update({"ts": time.time(), "data": issues})
        return issues
    except Exception as e:
        return [{"error": str(e)}]


def list_prs():
    if _PRS_CACHE["data"] and time.time() - _PRS_CACHE["ts"] < 20:
        return _PRS_CACHE["data"]
    try:
        out = subprocess.run(
            ["gh", "pr", "list", "--state", "open", "--limit", "60",
             "--json", "number,title,body,isDraft,headRefName,url,reviewDecision,mergeable,labels,statusCheckRollup,comments,author,createdAt,updatedAt"],
            capture_output=True, text=True, timeout=20, check=True,
        ).stdout
        prs = json.loads(out)
        for pr in prs:
            pr["labels"] = [l["name"] for l in pr.get("labels", [])]
            # rollup CI state
            checks = pr.get("statusCheckRollup") or []
            ci_states = [(c.get("conclusion") or c.get("status") or "").upper() for c in checks]
            failing_checks = []
            pending_checks = []
            for c in checks if isinstance(checks, list) else []:
                name = c.get("name") or c.get("context") or "check"
                state = (c.get("conclusion") or c.get("status") or "").upper()
                if state in ("FAILURE", "ERROR", "ACTION_REQUIRED"):
                    failing_checks.append(name)
                elif state not in ("SUCCESS", "COMPLETED", "NEUTRAL", "SKIPPED"):
                    pending_checks.append(name)
            if not ci_states:
                pr["ci"] = "none"
            elif any(s == "FAILURE" for s in ci_states):
                pr["ci"] = "fail"
            elif all(s in ("SUCCESS", "COMPLETED", "NEUTRAL", "SKIPPED") for s in ci_states):
                pr["ci"] = "pass"
            else:
                pr["ci"] = "pending"
            pr["failing_checks"] = failing_checks
            pr["pending_checks"] = pending_checks
            pr["body"] = pr.get("body") or ""
            pr["summary"] = _text_preview(pr["body"], 180) or "no body yet"
            author = pr.get("author") or {}
            pr["author"] = author.get("login") if isinstance(author, dict) else ""
            del pr["statusCheckRollup"]
            # Did codex already post a verdict? Look for our signature header.
            comments = pr.get("comments") or []
            pr["reviewed_by_codex"] = any(
                (c.get("body") or "").startswith("# Reviewer-agent verdict")
                for c in comments
            )
            # If we have a locally-saved comment URL, surface it.
            url_file = STATE_DIR / f"review-{pr['number']}.url"
            try:
                if url_file.exists():
                    pr["review_url"] = url_file.read_text().strip() or None
            except Exception:
                pass
            del pr["comments"]
        _PRS_CACHE.update({"ts": time.time(), "data": prs})
        return prs
    except Exception as e:
        return [{"error": str(e)}]


def invalidate_caches():
    _ISSUES_CACHE["ts"] = 0
    _PRS_CACHE["ts"] = 0


def prepare_pr_review(pr_num: int):
    """Build the reviewer prompt for a PR — mirrors orchestrate.sh's spawn_reviewer
    setup but inline so the dashboard can spawn the codex exec under a PTY
    instead of capturing its stdout to a file the user can't watch live."""
    if not (1 <= pr_num <= 9999):
        return {"error": "bad pr number"}
    # Pull PR body + diff via REST so GraphQL EOFs in gh pr view cannot block launch.
    try:
        meta = fetch_pr_meta(pr_num)
        body = f"Title: {meta.get('title') or ''}\n\n{meta.get('body') or ''}".strip()
    except Exception as e:
        return {"error": f"gh api PR #{pr_num}: {gh_error(e)}"}
    # Try several link patterns; fall back to "no linked issue" if none stick.
    issue_num = None
    for pat in (r"(?:Closes|Fixes|Resolves|Implements)\s+#(\d+)",
                r"#(\d+)"):                                    # last resort
        m = re.search(pat, body, re.IGNORECASE)
        if m:
            issue_num = m.group(1)
            break
    try:
        diff = fetch_pr_diff(pr_num)
    except Exception as e:
        return {"error": f"gh api PR diff #{pr_num}: {gh_error(e)}"}
    ibody = ""
    issue_fetch_error = ""
    if issue_num:
        try:
            ibody = fetch_issue_body(issue_num)
        except Exception as e:
            issue_fetch_error = gh_error(e)
            ibody = ""

    diff_file = STATE_DIR / f"pr-{pr_num}.diff"
    diff_file.write_text(diff)
    if issue_num:
        ibody_file = STATE_DIR / f"issue-{issue_num}.body.md"
        ibody_file.write_text(ibody)

    template_path = PROMPTS_DIR / "review.md"
    if not template_path.exists():
        return {"error": "prompts/review.md missing"}
    tpl = template_path.read_text()
    prompt = (
        tpl.replace("$PR_NUMBER", str(pr_num))
           .replace("$ISSUE_NUMBER", issue_num or "n/a")
           .replace("$DIFF", "(see PR diff section below)")
           .replace("$REPO_NAME", REPO_NAME)
        + "\n\n## PR body\n\n" + body
        + ("\n\n## Issue body (#" + issue_num + ")\n\n" + (ibody or f"_Linked issue fetch failed: {issue_fetch_error}_") if issue_num
           else "\n\n## Issue body\n\n_no `Closes #N` link in PR body - review based on PR body + diff alone_")
        + "\n\n## PR diff\n\n```diff\n" + diff + "\n```\n"
    )
    prompt_file = STATE_DIR / f"review-prompt-{pr_num}.md"
    prompt_file.write_text(prompt)
    return {
        "pr": pr_num,
        "issue": int(issue_num) if issue_num else None,
        "prompt_file": str(prompt_file),
        "diff_size": len(diff),
        "url": meta.get("url"),
    }


def prepare_merge(pr_num: int):
    """Render the merger prompt for a PR. Returns the prompt file path and
    the PR's head branch name so the wrapper can checkout if needed."""
    if not (1 <= pr_num <= 9999):
        return {"error": "bad pr number"}
    try:
        meta = fetch_pr_meta(pr_num)
    except Exception as e:
        return {"error": f"gh api PR #{pr_num}: {gh_error(e)}"}
    branch = meta.get("headRefName") or ""
    api_path = f"repos/{github_repo_slug()}/pulls/{pr_num}"
    template_path = PROMPTS_DIR / "merge.md"
    if not template_path.exists():
        return {"error": "prompts/merge.md missing"}
    tpl = template_path.read_text()
    prompt = (tpl.replace("$PR_NUMBER", str(pr_num))
                 .replace("$PR_BRANCH", branch)
                 .replace("$REPO_ROOT", str(REPO_ROOT))
                 .replace("$REPO_API_PATH", api_path)
                 .replace("$REPO_NAME", REPO_NAME))
    prompt_file = STATE_DIR / f"merge-prompt-{pr_num}.md"
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    prompt_file.write_text(prompt)
    return {
        "pr": pr_num,
        "branch": branch,
        "url": meta.get("url"),
        "api_path": api_path,
        "prompt_file": str(prompt_file),
    }


def prepare_proposal(slug_hint: str = ""):
    """Materialise the proposer prompt + an empty draft file.

    Unlike issue/PR prep this does not touch GitHub — it just renders the
    proposer template into state/ and points the wrapper at a fresh draft
    file the agent will fill in. Slug is for filenames only; the issue
    title comes out of the codex session.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", (slug_hint or "").lower()).strip("-")[:32]
    if not slug:
        slug = "draft-" + time.strftime("%Y%m%d-%H%M%S")
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    draft_file  = STATE_DIR / f"proposal-{slug}.md"
    prompt_file = STATE_DIR / f"proposal-prompt-{slug}.md"
    template_path = PROMPTS_DIR / "propose.md"
    if not template_path.exists():
        return {"error": "prompts/propose.md missing"}
    tpl = template_path.read_text()
    prompt = (tpl.replace("$DRAFT_FILE", str(draft_file))
                 .replace("$SLUG", slug)
                 .replace("$REPO_ROOT", str(REPO_ROOT))
                 .replace("$REPO_NAME", REPO_NAME))
    prompt_file.write_text(prompt)
    if not draft_file.exists():
        draft_file.write_text("")  # empty placeholder so $DRAFT_FILE always exists
    return {
        "slug": slug,
        "prompt_file": str(prompt_file),
        "draft_file": str(draft_file),
    }


def spawn_review(pr_num: int):
    if not (1 <= pr_num <= 9999):
        return {"error": "bad pr number"}
    script = PACKAGE_ROOT / "orchestrate.sh"
    log_file = STATE_DIR / f"review-spawn-{pr_num}.out"
    # Match the implementer: codex with gpt-5.4-mini for the verdict generation.
    # The reviewer agent doesn't need network — the diff + issue body are
    # already embedded in the prompt; orchestrate.sh captures stdout and posts
    # it via `gh pr comment` itself.
    env = os.environ.copy()
    env.setdefault("REVIEWER", "codex")
    env.setdefault("CODEX_MODEL", CODEX_MODEL)
    try:
        fh = open(log_file, "w")
        subprocess.Popen(
            [str(script), "--review", str(pr_num)],
            cwd=str(REPO_ROOT),
            stdout=fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            env=env,
            start_new_session=True,
        )
    except Exception as e:
        return {"error": f"spawn failed: {e}"}
    invalidate_caches()
    return {"started": True, "pr": pr_num, "log": f"review-spawn-{pr_num}.out",
            "reviewer": env["REVIEWER"], "model": env["CODEX_MODEL"]}


def merge_pr(pr_num: int, strategy: str = "squash"):
    if not (1 <= pr_num <= 9999):
        return {"error": "bad pr number"}
    if strategy not in ("squash", "merge", "rebase"):
        return {"error": "bad strategy"}
    try:
        # gh pr merge handles draft check internally; --squash is the safest default.
        result = subprocess.run(
            ["gh", "pr", "merge", str(pr_num), f"--{strategy}", "--delete-branch"],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            return {"error": (result.stderr or result.stdout or "merge failed").strip()}
    except Exception as e:
        return {"error": f"merge failed: {e}"}
    invalidate_caches()
    return {"merged": True, "pr": pr_num, "strategy": strategy, "output": result.stdout.strip()}


def list_running_orchestrators():
    """Find issue numbers currently being worked by checking for live worktrees with no commits OR active log mtime within last 60s."""
    out = []
    if not WORKTREES_DIR.exists():
        return out
    now = time.time()
    for p in sorted(WORKTREES_DIR.iterdir()):
        if not p.is_dir():
            continue
        m = re.match(r"(\d+)-", p.name)
        if not m:
            continue
        issue_num = m.group(1)
        log = STATE_DIR / f"implementer-{issue_num}.log"
        active = log.exists() and (now - log.stat().st_mtime) < 60
        out.append({"issue": issue_num, "worktree": p.name, "active": active})
    return out


def launch_orchestrator(issue_num: int, mode: str):
    """Spawn the orchestrator on an issue. mode is 'watch' or 'headless' — same effect; the flag is forwarded to clients so the UI knows whether to auto-switch."""
    if mode not in ("watch", "headless"):
        return {"error": "bad mode"}
    if not (1 <= issue_num <= 9999):
        return {"error": "bad issue number"}

    script = PACKAGE_ROOT / "orchestrate.sh"
    if not script.exists():
        return {"error": "orchestrate.sh missing"}

    log_file = STATE_DIR / f"orchestrator-{issue_num}.out"
    # If a fresh worktree exists, refuse — the orchestrator will refuse anyway.
    wt = WORKTREES_DIR / f"{issue_num}-*"
    import glob
    if glob.glob(str(wt)):
        return {"error": f"a worktree for issue {issue_num} already exists; clean it up first"}

    # Spawn the orchestrator detached. Use setsid so it survives the dashboard restarting.
    env = os.environ.copy()
    env.setdefault("AGENT_TIMEOUT", "1500")
    try:
        # nohup + & via the parent shell, but call the script directly via subprocess.Popen.
        fh = open(log_file, "w")
        subprocess.Popen(
            [str(script), str(issue_num)],
            cwd=str(REPO_ROOT),
            stdout=fh, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            env=env,
            start_new_session=True,
        )
    except Exception as e:
        return {"error": f"spawn failed: {e}"}

    # Invalidate issues cache so the in_progress label shows up fast.
    _ISSUES_CACHE["ts"] = 0
    return {
        "started": True,
        "issue": issue_num,
        "mode": mode,
        "orchestrator_log": f"orchestrator-{issue_num}.out",
        "implementer_log": f"implementer-{issue_num}.log",
    }


def list_worktrees():
    if not WORKTREES_DIR.exists():
        return []
    out = []
    for p in sorted(WORKTREES_DIR.iterdir()):
        if not p.is_dir():
            continue
        try:
            st = _worktree_status(p)
            commits = subprocess.run(
                ["git", "-C", str(p), "log", "--oneline", "origin/main..HEAD"],
                capture_output=True, text=True, timeout=5
            ).stdout.strip()
            commits_str = commits.split("\n")[0] if commits else ""
            if commits and len(commits.split("\n")) > 1:
                commits_str += f" (+{len(commits.split(chr(10))) - 1} more)"
            st.update({"name": p.name, "path": str(p), "commits": commits_str})
            out.append(st)
        except Exception as e:
            out.append({"name": p.name, "path": str(p), "commits": f"(error: {e})", "dirty": False, "status": "error", "safe_remove": False})
    def rank(w):
        order = {"merge candidate": 0, "clean": 1, "merged": 2, "dirty": 3, "error": 4}
        return (order.get(w.get("status"), 9), w.get("dirty"), w.get("name"))
    out.sort(key=rank)
    return out


def remove_worktree(name: str):
    if not name:
        return {"error": "name required"}
    wt = WORKTREES_DIR / name
    if not wt.exists():
        return {"error": "worktree not found"}
    if _pty_in_use(wt):
        return {"error": "worktree is in use by a live terminal"}
    st = _worktree_status(wt)
    if st["dirty"]:
        return {"error": "refusing to remove a dirty worktree"}
    if not st["safe_remove"]:
        return {"error": "worktree is not merged yet; keep it or merge first"}
    try:
        subprocess.run(
            ["git", "-C", str(REPO_ROOT), "worktree", "remove", str(wt)],
            capture_output=True, text=True, timeout=30, check=True,
        )
    except subprocess.CalledProcessError as e:
        return {"error": (e.stderr or e.stdout or "").strip() or "worktree remove failed"}
    except Exception as e:
        return {"error": f"worktree remove failed: {e}"}
    invalidate_caches()
    return {"removed": True, "name": name}


def prepare_ci_fix(pr_num: int):
    if not (1 <= pr_num <= 9999):
        return {"error": "bad pr number"}
    prs = list_prs()
    meta = next((pr for pr in prs if pr.get("number") == pr_num), None)
    if not meta:
        return {"error": f"PR #{pr_num} not found"}
    template_path = PROMPTS_DIR / "fix-ci.md"
    if not template_path.exists():
        return {"error": "prompts/fix-ci.md missing"}
    tpl = template_path.read_text()
    prompt = (
        tpl.replace("$PR_NUMBER", str(pr_num))
           .replace("$PR_BRANCH", meta.get("headRefName") or "")
           .replace("$PR_URL", meta.get("url") or "")
           .replace("$FAILING_CHECKS", ", ".join(meta.get("failing_checks") or []) or "none")
           .replace("$PENDING_CHECKS", ", ".join(meta.get("pending_checks") or []) or "none")
           .replace("$REPO_NAME", REPO_NAME)
    )
    prompt_file = STATE_DIR / f"fix-ci-prompt-{pr_num}.md"
    prompt_file.write_text(prompt)
    return {
        "pr": pr_num,
        "branch": meta.get("headRefName") or "",
        "url": meta.get("url") or "",
        "prompt_file": str(prompt_file),
        "failing_checks": meta.get("failing_checks") or [],
        "pending_checks": meta.get("pending_checks") or [],
    }


