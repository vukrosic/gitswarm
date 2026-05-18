"""GitHub CLI/API helpers for issues and pull requests."""
import json
import re
import subprocess
import time
from pathlib import Path


REPO_ROOT = None
STATE_DIR = None

_ISSUES_CACHE = {"ts": 0, "data": None}
_PRS_CACHE = {"ts": 0, "data": None}


def init(repo_root: Path, state_dir: Path):
    global REPO_ROOT, STATE_DIR
    REPO_ROOT = repo_root
    STATE_DIR = state_dir


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


def _normalize_milestone(raw):
    if not isinstance(raw, dict):
        return None
    return {
        "number": raw.get("number"),
        "title": raw.get("title") or "",
        "description": raw.get("description") or "",
        "state": raw.get("state") or "",
        "open_issues": raw.get("open_issues", raw.get("openIssues", 0)) or 0,
        "closed_issues": raw.get("closed_issues", raw.get("closedIssues", 0)) or 0,
        "due_on": raw.get("due_on", raw.get("dueOn")) or None,
        "created_at": raw.get("created_at", raw.get("createdAt")) or "",
        "updated_at": raw.get("updated_at", raw.get("updatedAt")) or "",
        "url": raw.get("url") or raw.get("html_url") or "",
    }


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


def gh_api_paginated(path, timeout=30, retries=2):
    try:
        raw = run_gh(["api", "--paginate", "--slurp", path], timeout=timeout, retries=retries)
        pages = json.loads(raw)
        if not isinstance(pages, list):
            return []
        out = []
        for page in pages:
            if isinstance(page, list):
                out.extend(page)
            elif page:
                out.append(page)
        return out
    except Exception:
        raw = gh_api_json(path, timeout=timeout, retries=retries)
        return raw if isinstance(raw, list) else []


def gh_api_text(path, headers=None, timeout=20, retries=2):
    args = ["api"]
    for header in headers or []:
        args.extend(["-H", header])
    args.append(path)
    return run_gh(args, timeout=timeout, retries=retries)


def _user_login(raw):
    user = raw.get("user") or raw.get("author") or {}
    if isinstance(user, dict):
        return user.get("login") or ""
    return str(user or "")


def _normalize_comment(raw):
    if not isinstance(raw, dict):
        return None
    return {
        "id": raw.get("id"),
        "author": _user_login(raw),
        "body": raw.get("body") or "",
        "url": raw.get("html_url") or raw.get("url") or "",
        "created_at": raw.get("created_at") or raw.get("createdAt") or "",
        "updated_at": raw.get("updated_at") or raw.get("updatedAt") or "",
    }


def _normalize_review(raw):
    if not isinstance(raw, dict):
        return None
    return {
        "id": raw.get("id"),
        "author": _user_login(raw),
        "state": raw.get("state") or "",
        "body": raw.get("body") or "",
        "url": raw.get("html_url") or raw.get("url") or "",
        "submitted_at": raw.get("submitted_at") or raw.get("submittedAt") or "",
    }


def _normalize_review_comment(raw):
    comment = _normalize_comment(raw)
    if not comment:
        return None
    comment.update({
        "path": raw.get("path") or "",
        "line": raw.get("line") or raw.get("original_line"),
        "diff_hunk": raw.get("diff_hunk") or "",
    })
    return comment


def fetch_pr_meta(pr_num: int):
    slug = github_repo_slug()
    raw = gh_api_json(f"repos/{slug}/pulls/{pr_num}", timeout=20, retries=2)
    meta = {
        "number": raw.get("number"),
        "title": raw.get("title") or "",
        "body": raw.get("body") or "",
        "url": raw.get("html_url"),
        "headRefName": (raw.get("head") or {}).get("ref") or "",
        "head": (raw.get("head") or {}).get("ref") or "",
        "base": (raw.get("base") or {}).get("ref") or "",
        "author": ((raw.get("user") or {}).get("login") or ""),
        "isDraft": bool(raw.get("draft")),
        "mergeable": raw.get("mergeable"),
        "state": raw.get("state"),
        "mergedAt": raw.get("merged_at"),
        "reviewDecision": "",
        "comments": [],
        "reviews": [],
        "review_comments": [],
    }
    try:
        reviews = gh_api_paginated(f"repos/{slug}/pulls/{pr_num}/reviews?per_page=100", timeout=30, retries=1)
        meta["reviews"] = [item for item in (_normalize_review(review) for review in reviews) if item]
        latest_by_user = {}
        for review in meta["reviews"]:
            user = review.get("author") or ""
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
    try:
        comments = gh_api_paginated(f"repos/{slug}/issues/{pr_num}/comments?per_page=100", timeout=30, retries=1)
        meta["comments"] = [item for item in (_normalize_comment(comment) for comment in comments) if item]
    except Exception:
        pass
    try:
        review_comments = gh_api_paginated(f"repos/{slug}/pulls/{pr_num}/comments?per_page=100", timeout=30, retries=1)
        meta["review_comments"] = [
            item for item in (_normalize_review_comment(comment) for comment in review_comments) if item
        ]
    except Exception:
        pass
    return meta


def fetch_issue_meta(issue_num):
    slug = github_repo_slug()
    raw = gh_api_json(f"repos/{slug}/issues/{issue_num}", timeout=15, retries=2)
    labels = [
        label.get("name")
        for label in raw.get("labels", [])
        if isinstance(label, dict) and label.get("name")
    ]
    comments = gh_api_paginated(f"repos/{slug}/issues/{issue_num}/comments?per_page=100", timeout=30, retries=1)
    body = raw.get("body") or ""
    return {
        "number": raw.get("number"),
        "body": body,
        "title": raw.get("title") or "",
        "state": raw.get("state") or "",
        "url": raw.get("html_url") or "",
        "labels": labels,
        "assignees": [a.get("login") for a in raw.get("assignees", []) if isinstance(a, dict) and a.get("login")],
        "author": ((raw.get("user") or {}).get("login") or ""),
        "created_at": raw.get("created_at") or "",
        "updated_at": raw.get("updated_at") or "",
        "in_progress": "in-progress" in labels,
        "claim_next": "claim-next" in labels,
        "parked": "needs-validation" in labels,
        "summary": _text_preview(body, 180) or "no body yet",
        "suggested_labels": _issue_label_suggestions(raw.get("title") or "", body),
        "comment_count": raw.get("comments") or 0,
        "comments": [item for item in (_normalize_comment(comment) for comment in comments) if item],
        "milestone": _normalize_milestone(raw.get("milestone")),
    }


def fetch_issue_body(issue_num: str):
    return fetch_issue_meta(issue_num).get("body") or ""


def update_issue(issue_num: int, title=None, body=None, state=None):
    if not (1 <= issue_num <= 9999):
        return {"error": "bad issue number"}
    slug = github_repo_slug()
    args = ["api", "-X", "PATCH"]
    if title is not None:
        args.extend(["-f", f"title={title}"])
    if body is not None:
        args.extend(["-f", f"body={body}"])
    if state is not None:
        args.extend(["-f", f"state={state}"])
    args.append(f"repos/{slug}/issues/{issue_num}")
    try:
        raw = run_gh(args, timeout=20, retries=2)
        invalidate_caches()
        return json.loads(raw)
    except Exception as e:
        return {"error": gh_error(e)}


def close_issue(issue_num: int):
    return update_issue(issue_num, state="closed")


def create_issue(title: str, body: str = ""):
    title = (title or "").strip()
    if not title:
        return {"error": "title is required"}
    slug = github_repo_slug()
    args = ["issue", "create", "--repo", slug, "--title", title]
    args.extend(["--body", body or ""])
    try:
        out = run_gh(args, timeout=30, retries=2).strip()
        invalidate_caches()
        m = re.search(r"/issues/(\d+)", out)
        return {
            "number": int(m.group(1)) if m else None,
            "url": out or "",
            "title": title,
        }
    except Exception as e:
        return {"error": gh_error(e)}


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
             "--limit", "100", "--json", "number,title,body,labels,url,author,assignees,comments,createdAt,updatedAt,state,milestone"],
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
            it["milestone"] = _normalize_milestone(it.get("milestone"))
            it["summary"] = _text_preview(it["body"], 180) or "no body yet"
            it["suggested_labels"] = _issue_label_suggestions(it.get("title") or "", it["body"])
            author = it.get("author") or {}
            it["author"] = author.get("login") if isinstance(author, dict) else ""
            raw_comments = it.get("comments") or []
            it["comment_count"] = len(raw_comments) if isinstance(raw_comments, list) else 0
            it.pop("comments", None)
        _ISSUES_CACHE.update({"ts": time.time(), "data": issues})
        return issues
    except Exception as e:
        return [{"error": str(e)}]


def list_milestones():
    try:
        slug = github_repo_slug()
        raw = gh_api_json(f"repos/{slug}/milestones?state=all&per_page=100", timeout=20, retries=2)
        milestones = []
        for item in raw if isinstance(raw, list) else []:
            milestone = _normalize_milestone(item)
            if milestone:
                milestones.append(milestone)
        milestones.sort(key=lambda item: (
            0 if item.get("state") == "open" else 1,
            item.get("due_on") or "9999-12-31T23:59:59Z",
            item.get("number") or 0,
            item.get("title") or "",
        ))
        return milestones
    except Exception as e:
        return [{"error": str(e)}]


def list_prs():
    if _PRS_CACHE["data"] and time.time() - _PRS_CACHE["ts"] < 20:
        return _PRS_CACHE["data"]
    try:
        out = subprocess.run(
            ["gh", "pr", "list", "--state", "open", "--limit", "60",
             "--json", "number,title,body,isDraft,headRefName,baseRefName,url,reviewDecision,mergeable,labels,statusCheckRollup,comments,author,createdAt,updatedAt"],
            capture_output=True, text=True, timeout=20, check=True,
        ).stdout
        prs = json.loads(out)
        for pr in prs:
            pr["labels"] = [l["name"] for l in pr.get("labels", [])]
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
            pr["head"] = pr.get("headRefName") or ""
            pr["base"] = pr.get("baseRefName") or ""
            author = pr.get("author") or {}
            pr["author"] = author.get("login") if isinstance(author, dict) else ""
            del pr["statusCheckRollup"]
            comments = pr.get("comments") or []
            pr["reviewed_by_codex"] = any(
                (c.get("body") or "").startswith("# Reviewer-agent verdict")
                for c in comments
            )
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
