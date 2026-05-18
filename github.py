#!/usr/bin/env python3
"""GitHub, issue, PR, and worktree helpers for gitswarm."""
import json
import os
import re
import shlex
import subprocess
import time
from pathlib import Path

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

from backend.pty_runtime import (
    init as _init_pty_runtime,
    spawn_pty,
    pty_write,
    pty_resize,
    pty_read,
    kill_pty,
    delete_pty,
    list_ptys,
    live_issue_pty,
    reap_dead_ptys,
    pty_in_use,
    spawn_shell_session,
)
from backend.github_remote import (
    init as _init_github_remote,
    gh_error,
    is_transient_gh_error,
    run_gh,
    github_repo_slug,
    gh_api_json,
    gh_api_text,
    fetch_pr_meta,
    fetch_issue_meta,
    fetch_issue_body,
    update_issue,
    close_issue,
    create_issue,
    fetch_pr_diff,
    list_issues,
    list_prs,
    invalidate_caches,
)

_init_pty_runtime(REPO_ROOT, USER_SHELL)
_init_github_remote(REPO_ROOT, STATE_DIR)


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
    return pty_in_use(worktree_path)


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


def prepare_issue_review(issue_num: int):
    """Build a review prompt for an issue and persist the body for the agent.

    The issue reviewer comment is a GitHub issue comment, not a PR comment, so
    we keep the prompt focused on whether the issue is ready to implement.
    """
    if not (1 <= issue_num <= 9999):
        return {"error": "bad issue number"}
    try:
        meta = fetch_issue_meta(issue_num)
    except Exception as e:
        return {"error": f"gh api issue #{issue_num}: {gh_error(e)}"}
    body = meta.get("body") or ""
    title = meta.get("title") or ""

    template_path = PROMPTS_DIR / "review-issue.md"
    if not template_path.exists():
        return {"error": "prompts/review-issue.md missing"}
    tpl = template_path.read_text()
    prompt = (
        tpl.replace("$ISSUE_NUMBER", str(issue_num))
           .replace("$ISSUE_TITLE", title)
           .replace("$ISSUE_BODY", body)
           .replace("$REPO_NAME", REPO_NAME)
    )
    prompt_file = STATE_DIR / f"review-issue-prompt-{issue_num}.md"
    prompt_file.write_text(prompt)
    return {
        "issue": issue_num,
        "prompt_file": str(prompt_file),
        "body_size": len(body),
        "url": meta.get("url"),
    }


def extract_issue_review_comment(text: str):
    """Pull the markdown verdict block out of the PTY transcript.

    The issue reviewer prompt requires the verdict to start with
    `# Reviewer-agent verdict`. We trim any wrapper noise before that marker
    and stop before the server-side exit banner if it appears.
    """
    if not text:
        return ""
    start = text.find("# Reviewer-agent verdict")
    if start < 0:
        return ""
    tail = text[start:]
    end = tail.find("\n────")
    if end >= 0:
        tail = tail[:end]
    return tail.strip()


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
    # Pull the merged main into local so the repo is up-to-date.
    subprocess.run(
        ["git", "-C", str(REPO_ROOT), "fetch", "origin", "main"],
        capture_output=True, timeout=30,
    )
    subprocess.run(
        ["git", "-C", str(REPO_ROOT), "merge", "--ff-only", "origin/main"],
        capture_output=True, timeout=30,
    )
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
