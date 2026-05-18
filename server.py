#!/usr/bin/env python3
"""gitswarm dashboard server."""
import importlib.util
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_GITHUB_SPEC = importlib.util.spec_from_file_location("gitswarm_github", _HERE / "github.py")
if _GITHUB_SPEC is None or _GITHUB_SPEC.loader is None:
    raise RuntimeError("unable to load github.py")
_GITHUB = importlib.util.module_from_spec(_GITHUB_SPEC)
_GITHUB_SPEC.loader.exec_module(_GITHUB)
globals().update({k: v for k, v in vars(_GITHUB).items() if not k.startswith("_")})

_UI_SPEC = importlib.util.spec_from_file_location("gitswarm_ui", _HERE / "ui.py")
if _UI_SPEC is None or _UI_SPEC.loader is None:
    raise RuntimeError("unable to load ui.py")
_UI = importlib.util.module_from_spec(_UI_SPEC)
_UI_SPEC.loader.exec_module(_UI)
RAW_INDEX_HTML = _UI.INDEX_HTML

INDEX_HTML = RAW_INDEX_HTML.replace("__REPO_NAME__", REPO_NAME)

def _slugify(text, limit=40):
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug[:limit] or "prompt"

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quieter
        pass

    def _send_json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/" or u.path == "/index.html":
            body = INDEX_HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if u.path == "/api/files":
            return self._send_json({"files": list_state_files()})
        if u.path == "/api/worktrees":
            return self._send_json({"worktrees": list_worktrees(), "running": list_running_orchestrators()})
        if u.path == "/api/issue":
            qs = dict(p.split("=", 1) for p in (u.query.split("&") if u.query else []) if "=" in p)
            try:
                num = int(unquote(qs.get("num", "")))
            except ValueError:
                return self._send_json({"error": "bad num"}, 400)
            if not (1 <= num <= 9999):
                return self._send_json({"error": "bad num"}, 400)
            try:
                return self._send_json(fetch_issue_meta(num))
            except Exception as e:
                return self._send_json({"error": gh_error(e)}, 500)
        if u.path == "/api/pr/diff":
            qs = dict(p.split("=", 1) for p in (u.query.split("&") if u.query else []) if "=" in p)
            try:
                num = int(unquote(qs.get("num", "")))
            except ValueError:
                return self._send_json({"error": "bad num"}, 400)
            if not (1 <= num <= 9999):
                return self._send_json({"error": "bad num"}, 400)
            try:
                return self._send_json({"number": num, "diff": fetch_pr_diff(num)})
            except Exception as e:
                return self._send_json({"error": gh_error(e)}, 500)

        if u.path == "/api/agents":
            # List configured agents + which binaries are actually installed.
            import shutil as _sh
            out = []
            for aid, cfg in AGENTS.items():
                out.append({
                    "id": aid,
                    "label": cfg["label"],
                    "bin": cfg["bin"],
                    "model": cfg.get("model") or "",
                    "available": _sh.which(cfg["bin"]) is not None,
                })
            return self._send_json({"agents": out, "default": DEFAULT_AGENT,
                                    "code_mtime": max(
                                        (_HERE / "ui.py").stat().st_mtime,
                                        (_HERE / "server.py").stat().st_mtime,
                                        (_HERE / "github.py").stat().st_mtime,
                                    )})
        if u.path == "/api/issues":
            return self._send_json({"issues": list_issues()})
        if u.path == "/api/prs":
            return self._send_json({"prs": list_prs()})
        if u.path == "/api/pty/list":
            reap_dead_ptys()
            return self._send_json({"sessions": list_ptys()})
        if u.path == "/api/pty/stream":
            qs = dict(p.split("=", 1) for p in (u.query.split("&") if u.query else []) if "=" in p)
            sid = unquote(qs.get("sid", ""))
            try:
                offset = max(0, int(qs.get("offset", "0") or 0))
            except ValueError:
                return self._send_json({"error": "bad offset"}, 400)
            try:
                timeout = max(1, min(25, int(qs.get("timeout", "15") or 15)))
            except ValueError:
                timeout = 15
            res = pty_read(sid, offset, timeout=timeout)
            if res is None:
                return self._send_json({"error": "unknown sid"}, 404)
            data, logical_len, alive, drop, reset = res
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("X-Offset", str(logical_len))
            self.send_header("X-Alive", "1" if alive else "0")
            self.send_header("X-Drop", str(drop))
            self.send_header("X-Reset", "1" if reset else "0")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if u.path == "/api/file":
            qs = dict(p.split("=", 1) for p in (u.query.split("&") if u.query else []) if "=" in p)
            name = unquote(qs.get("name", ""))
            offset = max(0, int(qs.get("offset", "0") or 0))
            if not name or "/" in name or ".." in name:
                return self._send_json({"error": "bad name"}, 400)
            fp = STATE_DIR / name
            if not fp.exists() or not fp.is_file():
                return self._send_json({"error": "not found"}, 404)
            size = fp.stat().st_size
            if offset >= size:
                body = b""
            else:
                with fp.open("rb") as fh:
                    fh.seek(offset)
                    data = fh.read()
                # If client is starting fresh on a huge file, only send the last 2MB so the
                # browser doesn't get hammered. Incremental polls (offset > 0) always send all.
                if offset == 0 and len(data) > 2_000_000:
                    data = b"[\xe2\x80\xa6truncated to last 2MB\xe2\x80\xa6]\n" + data[-2_000_000:]
                body = data
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Total-Size", str(size))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        u = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length).decode() if content_length else ""
        try:
            payload = json.loads(body or "{}")
        except json.JSONDecodeError:
            return self._send_json({"error": "bad json"}, 400)

        if u.path == "/api/launch":
            try:
                issue = int(payload.get("issue"))
            except (TypeError, ValueError):
                return self._send_json({"error": "issue must be int"}, 400)
            mode = payload.get("mode", "watch")
            result = launch_orchestrator(issue, mode)
            return self._send_json(result, 200 if result.get("started") else 400)

        if u.path == "/api/review":
            try:
                pr = int(payload.get("pr"))
            except (TypeError, ValueError):
                return self._send_json({"error": "pr must be int"}, 400)
            result = spawn_review(pr)
            return self._send_json(result, 200 if result.get("started") else 400)

        if u.path == "/api/merge":
            try:
                pr = int(payload.get("pr"))
            except (TypeError, ValueError):
                return self._send_json({"error": "pr must be int"}, 400)
            strategy = payload.get("strategy", "squash")
            result = merge_pr(pr, strategy)
            return self._send_json(result, 200 if result.get("merged") else 400)

        if u.path == "/api/issue/update":
            try:
                issue = int(payload.get("issue"))
            except (TypeError, ValueError):
                return self._send_json({"error": "issue must be int"}, 400)
            title = payload.get("title")
            body_text = payload.get("body")
            result = update_issue(issue, title=title, body=body_text)
            status = 200 if not result.get("error") else 400
            return self._send_json(result, status)

        if u.path == "/api/issue/delete":
            try:
                issue = int(payload.get("issue"))
            except (TypeError, ValueError):
                return self._send_json({"error": "issue must be int"}, 400)
            result = close_issue(issue)
            status = 200 if not result.get("error") else 400
            return self._send_json(result, status)

        if u.path == "/api/issue/create":
            title = payload.get("title", "")
            body_text = payload.get("body", "")
            result = create_issue(title, body=body_text)
            status = 200 if not result.get("error") else 400
            return self._send_json(result, status)

        if u.path == "/api/pty/new":
            kind = payload.get("kind", "shell")
            rows = int(payload.get("rows") or 30)
            cols = int(payload.get("cols") or 120)
            if kind == "shell":
                cwd_in = payload.get("cwd")
                if not cwd_in:
                    cwd_path = REPO_ROOT.resolve()
                else:
                    p = Path(cwd_in)
                    if not p.is_absolute():
                        p = REPO_ROOT / p
                    cwd_path = p.resolve()
                # Sandbox: cwd must be inside REPO_ROOT.
                try:
                    cwd_path.relative_to(REPO_ROOT.resolve())
                except ValueError:
                    return self._send_json({"error": "cwd must be inside repo"}, 400)
                env_extra = {"PS1": "\\[\\e[36m\\]agent\\[\\e[0m\\]:\\W$ "}
                res = spawn_shell_session(cwd_path, env_extra=env_extra)
                if res.get("error"):
                    return self._send_json(res, 400)
                # Apply requested geometry
                pty_resize(res["sid"], rows, cols)
                return self._send_json(res)

            if kind == "agent-shell":
                # Open the selected CLI agent (codex / claude / cmf) in the
                # repo root with NO prompt — an interactive REPL. When the
                # agent exits, drop into a bash shell rather than closing the
                # session, so the user can keep working in the same PTY.
                cwd_in = payload.get("cwd")
                if not cwd_in:
                    cwd_path = REPO_ROOT.resolve()
                else:
                    p = Path(cwd_in)
                    if not p.is_absolute():
                        p = REPO_ROOT / p
                    cwd_path = p.resolve()
                try:
                    cwd_path.relative_to(REPO_ROOT.resolve())
                except ValueError:
                    return self._send_json({"error": "cwd must be inside repo"}, 400)

                agent = resolve_agent(
                    payload.get("agent"),
                    override_model=payload.get("model"),
                    override_bin=payload.get("bin"),
                    override_yolo=payload.get("yolo_flag"),
                )
                # Same launch shape as the agent-with-prompt paths, but the
                # final argv is just `bin yolo [-m model]` — no prompt.
                parts = [shlex.quote(agent["bin"])]
                if agent.get("yolo"):
                    parts.append(agent["yolo"])
                if agent.get("model_flag") and agent.get("model"):
                    parts.extend([agent["model_flag"], shlex.quote(agent["model"])])
                agent_cmd = " ".join(parts)

                env_extra = {
                    "PS1": "\\[\\e[36m\\]" + agent["id"] + "\\[\\e[0m\\]:\\W$ ",
                }
                wrapper = (
                    'echo "──── starting {bin} ({yolo_short}) — interactive ────"; '
                    'echo "      agent:  {agent_label}"; '
                    'echo "      model:  {model}"; '
                    'echo "      cwd:    $(pwd)"; '
                    'echo "────"; '
                    '{agent_cmd}; '
                    'ec=$?; '
                    'echo; '
                    'echo "──── {bin} exited (code $ec) — dropping to shell ────"; '
                    'exec {shell} -i'
                ).format(
                    bin=shlex.quote(agent["bin"]),
                    yolo_short=agent_short(agent),
                    agent_label=agent["label"],
                    model=agent.get("model") or "(agent default)",
                    agent_cmd=agent_cmd,
                    shell=shlex.quote(USER_SHELL),
                )
                argv = ["bash", "-c", wrapper]
                sess = spawn_pty(argv, cwd=str(cwd_path), env_extra=env_extra,
                                 label=f"{agent['id']} · {cwd_path.name}",
                                 meta={"kind": "agent-shell", "agent": agent["id"]},
                                 rows=rows, cols=cols)
                return self._send_json({
                    "sid": sess["sid"],
                    "label": sess["label"],
                    "cwd": sess["cwd"],
                    "agent": agent["id"],
                    "model": agent.get("model"),
                })
            if kind == "agent-prompt":
                issue_num = None
                if payload.get("issue") not in (None, "", 0, "0"):
                    try:
                        issue_num = int(payload.get("issue"))
                    except (TypeError, ValueError):
                        return self._send_json({"error": "issue must be int"}, 400)
                    existing = live_issue_pty(issue_num)
                    if existing:
                        meta = existing.get("meta") or {}
                        agent = resolve_agent(
                            payload.get("agent"),
                            override_model=payload.get("model"),
                            override_bin=payload.get("bin"),
                            override_yolo=payload.get("yolo_flag"),
                        )
                        return self._send_json({
                            "sid": existing["sid"],
                            "label": existing.get("label") or f"#{issue_num}",
                            "cwd": existing.get("cwd") or "",
                            "issue": issue_num,
                            "branch": meta.get("branch"),
                            "worktree": meta.get("worktree"),
                            "prompt_file": meta.get("prompt_file"),
                            "agent": agent["id"],
                            "model": agent.get("model"),
                            "reused": True,
                        })

                cwd_in = payload.get("cwd")
                prompt = (payload.get("prompt") or "").strip()
                if not prompt:
                    return self._send_json({"error": "prompt is required"}, 400)

                prep = None
                cwd_path = None
                if issue_num is not None and not cwd_in:
                    prep = prepare_issue_worktree(issue_num)
                    if prep.get("error"):
                        return self._send_json(prep, 400)
                    cwd_path = Path(prep["worktree"]).resolve()
                else:
                    if not cwd_in:
                        cwd_path = REPO_ROOT.resolve()
                    else:
                        p = Path(cwd_in)
                        if not p.is_absolute():
                            p = REPO_ROOT / p
                        cwd_path = p.resolve()
                    try:
                        cwd_path.relative_to(REPO_ROOT.resolve())
                    except ValueError:
                        return self._send_json({"error": "cwd must be inside repo"}, 400)

                agent = resolve_agent(
                    payload.get("agent"),
                    override_model=payload.get("model"),
                    override_bin=payload.get("bin"),
                    override_yolo=payload.get("yolo_flag"),
                )
                prompt_slug = _slugify(payload.get("label") or prompt)
                prompt_file = STATE_DIR / f"prompt-{secrets.token_hex(4)}-{prompt_slug}.md"
                prompt_file.write_text(prompt)
                agent_cmd = build_agent_cmd(agent, f"$(cat {shlex.quote(str(prompt_file))})")

                env_extra = {
                    "PROMPT_FILE": str(prompt_file),
                    "PS1": "\\[\\e[36m\\]" + agent["id"] + "\\[\\e[0m\\]:\\W$ ",
                }
                if issue_num is not None:
                    env_extra["AGENT_ISSUE"] = str(issue_num)
                    if prep:
                        env_extra["AGENT_BRANCH"] = prep.get("branch", "")
                        env_extra["AGENT_PROMPT_FILE"] = prompt_file
                        env_extra["AGENT_WORKTREE"] = prep.get("worktree", "")
                wrapper = (
                    'echo "──── starting {bin} ({yolo_short}) — prompt ────"; '
                    'echo "      agent:  {agent_label}"; '
                    'echo "      model:  {model}"; '
                    'echo "      issue:  {issue_info}"; '
                    'echo "      prompt: $PROMPT_FILE"; '
                    'echo "      cwd:    $(pwd)"; '
                    'echo "────"; '
                    '{agent_cmd}; '
                    'ec=$?; '
                    'echo; '
                    'echo "──── {bin} exited (code $ec) — dropping to shell ────"; '
                    'exec {shell} -i'
                ).format(
                    bin=shlex.quote(agent["bin"]),
                    yolo_short=agent_short(agent),
                    agent_label=agent["label"],
                    model=agent.get("model") or "(agent default)",
                    issue_info=("#" + str(issue_num)) if issue_num is not None else "(none)",
                    agent_cmd=agent_cmd,
                    shell=shlex.quote(USER_SHELL),
                )
                argv = ["bash", "-c", wrapper]
                sess = spawn_pty(
                    argv,
                    cwd=str(cwd_path),
                    env_extra=env_extra,
                    label=f"{agent['id']} #{issue_num} · {prompt_slug}" if issue_num is not None else f"{agent['id']} · {prompt_slug}",
                    rows=rows,
                    cols=cols,
                    meta={
                        "kind": "prompt",
                        "agent": agent["id"],
                        "prompt_file": str(prompt_file),
                        "cwd": str(cwd_path),
                        "issue": issue_num,
                        "branch": (prep or {}).get("branch", ""),
                        "worktree": (prep or {}).get("worktree", ""),
                    },
                )
                return self._send_json({
                    "sid": sess["sid"],
                    "label": sess["label"],
                    "cwd": sess["cwd"],
                    "agent": agent["id"],
                    "model": agent.get("model"),
                    "prompt_file": str(prompt_file),
                    "prompt": prompt,
                    "issue": issue_num,
                    "branch": (prep or {}).get("branch", ""),
                    "worktree": (prep or {}).get("worktree", ""),
                })
            if kind == "pr-review":
                try:
                    pr = int(payload.get("pr"))
                except (TypeError, ValueError):
                    return self._send_json({"error": "pr must be int"}, 400)
                prep = prepare_pr_review(pr)
                if prep.get("error"):
                    return self._send_json(prep, 400)
                prompt_file = prep["prompt_file"]
                review_out  = STATE_DIR / f"review-{pr}.md"

                agent = resolve_agent(
                    payload.get("agent"),
                    override_model=payload.get("model"),
                    override_bin=payload.get("bin"),
                    override_yolo=payload.get("yolo_flag"),
                )
                agent_cmd = build_agent_cmd(agent, f"$(cat {shlex.quote(prompt_file)})")

                pr_url_file = STATE_DIR / f"review-{pr}.url"
                pr_url_file.unlink(missing_ok=True)
                env_extra = {
                    "PR_NUMBER": str(pr),
                    "REVIEW_OUT": str(review_out),
                    "REVIEW_URL_FILE": str(pr_url_file),
                    "PROMPT_FILE": prompt_file,
                    "PS1": "\\[\\e[35m\\]review·PR#" + str(pr) + "\\[\\e[0m\\]:\\W$ ",
                }

                # Interactive agent run. The reviewer prompt instructs the agent
                # to WRITE its verdict to $REVIEW_OUT and exit (not echo to chat),
                # so we get a clean markdown file we can auto-post after exit.
                wrapper = (
                    'touch $REVIEW_OUT; '
                    'echo "──── starting {bin} ({yolo_short}) review of PR #{pr} ────"; '
                    'echo "      agent:  {agent_label}"; '
                    'echo "      model:  {model}"; '
                    'echo "      prompt: $PROMPT_FILE"; '
                    'echo "      out:    $REVIEW_OUT  (agent writes verdict here)"; '
                    'echo "────"; '
                    '{agent_cmd}; '
                    'ec=$?; '
                    'echo; '
                    'echo "──── {bin} exited (code $ec) ────"; '
                    'if [ -s "$REVIEW_OUT" ]; then '
                        'echo "  $REVIEW_OUT has $(wc -l < $REVIEW_OUT) lines — posting to PR #{pr}…"; '
                        'url=$(gh pr comment {pr} -F $REVIEW_OUT 2>&1); '
                        'echo "  $url"; '
                        'echo "$url" | grep -Eo \'https://github.com/[^ ]+\' | head -1 > $REVIEW_URL_FILE; '
                        'echo "  comment url saved to $REVIEW_URL_FILE"; '
                    'else '
                        'echo "  $REVIEW_OUT is empty — agent did not produce a verdict file."; '
                        'echo "  to post manually: gh pr comment {pr} -F $REVIEW_OUT (after writing it)"; '
                    'fi; '
                    'echo; '
                    'exec {shell} -i'
                ).format(
                    pr=pr,
                    agent_label=agent["label"],
                    model=agent.get("model") or "(agent default)",
                    bin=shlex.quote(agent["bin"]),
                    yolo_short=agent_short(agent),
                    agent_cmd=agent_cmd,
                    shell=shlex.quote(USER_SHELL),
                )
                argv = ["bash", "-c", wrapper]
                sess = spawn_pty(argv, cwd=str(REPO_ROOT),
                                 env_extra=env_extra,
                                 label=f"{agent['id']} review · PR #{pr}",
                                 rows=rows, cols=cols)
                return self._send_json({
                    "sid": sess["sid"],
                    "label": sess["label"],
                    "cwd": sess["cwd"],
                    "pr": pr,
                    "pr_url": prep.get("url"),
                    "issue": prep.get("issue"),
                    "agent": agent["id"],
                    "model": agent.get("model"),
                    "prompt_file": prompt_file,
                    "review_out": str(review_out),
                    "review_url_file": str(pr_url_file),
                })

            if kind == "merge-pr":
                try:
                    pr = int(payload.get("pr"))
                except (TypeError, ValueError):
                    return self._send_json({"error": "pr must be int"}, 400)
                prep = prepare_merge(pr)
                if prep.get("error"):
                    return self._send_json(prep, 400)
                prompt_file = prep["prompt_file"]
                branch = prep["branch"]
                pr_url = prep.get("url")
                api_path = prep.get("api_path") or f"repos/{github_repo_slug()}/pulls/{pr}"

                agent = resolve_agent(
                    payload.get("agent"),
                    override_model=payload.get("model"),
                    override_bin=payload.get("bin"),
                    override_yolo=payload.get("yolo_flag"),
                )
                agent_cmd = build_agent_cmd(agent, f"$(cat {shlex.quote(prompt_file)})")

                env_extra = {
                    "PR_NUMBER": str(pr),
                    "PR_BRANCH": branch,
                    "REPO_API_PATH": api_path,
                    "PROMPT_FILE": prompt_file,
                    "PS1": "\\[\\e[31m\\]merge·PR#" + str(pr) + "\\[\\e[0m\\]:\\W$ ",
                }
                wrapper = (
                    'echo "──── starting {bin} ({yolo_short}) merge of PR #{pr} ────"; '
                    'echo "      agent:  {agent_label}"; '
                    'echo "      model:  {model}"; '
                    'echo "      branch: $PR_BRANCH"; '
                    'echo "      prompt: $PROMPT_FILE"; '
                    'echo "────"; '
                    '{agent_cmd}; '
                    'ec=$?; '
                    'echo; '
                    'echo "──── {bin} exited (code $ec) — dropping to shell ────"; '
                    'echo "  PR state: $(gh api {api_path_q} --jq \'.state + (if .merged_at then \" (merged \" + .merged_at + \")\" else \"\" end)\' 2>/dev/null)"; '
                    'exec {shell} -i'
                ).format(
                    pr=pr,
                    agent_label=agent["label"],
                    model=agent.get("model") or "(agent default)",
                    bin=shlex.quote(agent["bin"]),
                    yolo_short=agent_short(agent),
                    agent_cmd=agent_cmd,
                    api_path_q=shlex.quote(api_path),
                    shell=shlex.quote(USER_SHELL),
                )
                argv = ["bash", "-c", wrapper]
                sess = spawn_pty(argv, cwd=str(REPO_ROOT),
                                 env_extra=env_extra,
                                 label=f"{agent['id']} merge · PR #{pr}",
                                 rows=rows, cols=cols)
                return self._send_json({
                    "sid": sess["sid"],
                    "label": sess["label"],
                    "cwd": sess["cwd"],
                    "pr": pr,
                    "pr_url": pr_url,
                    "branch": branch,
                    "api_path": api_path,
                    "agent": agent["id"],
                    "model": agent.get("model"),
                    "prompt_file": prompt_file,
                })

            if kind == "ci-fix":
                try:
                    pr = int(payload.get("pr"))
                except (TypeError, ValueError):
                    return self._send_json({"error": "pr must be int"}, 400)
                prep = prepare_ci_fix(pr)
                if prep.get("error"):
                    return self._send_json(prep, 400)
                prompt_file = prep["prompt_file"]
                agent = resolve_agent(
                    payload.get("agent"),
                    override_model=payload.get("model"),
                    override_bin=payload.get("bin"),
                    override_yolo=payload.get("yolo_flag"),
                )
                agent_cmd = build_agent_cmd(agent, '$(cat "$PROMPT_FILE")')

                env_extra = {
                    "PR_NUMBER": str(pr),
                    "PR_BRANCH": prep.get("branch", ""),
                    "PR_URL": prep.get("url", ""),
                    "PROMPT_FILE": prompt_file,
                    "PS1": "\\[\\e[34m\\]fix-ci·PR#" + str(pr) + "\\[\\e[0m\\]:\\W$ ",
                }
                wrapper = (
                    'echo "──── starting {bin} ({yolo_short}) CI fix for PR #{pr} ────"; '
                    'echo "      agent:  {agent_label}"; '
                    'echo "      model:  {model}"; '
                    'echo "      branch: $PR_BRANCH"; '
                    'echo "      prompt: $PROMPT_FILE"; '
                    'echo "      checks: {checks}"; '
                    'echo "────"; '
                    '{agent_cmd}; '
                    'ec=$?; '
                    'echo; '
                    'echo "──── {bin} exited (code $ec) — dropping to shell ────"; '
                    'exec {shell} -i'
                ).format(
                    pr=pr,
                    agent_label=agent["label"],
                    model=agent.get("model") or "(agent default)",
                    bin=shlex.quote(agent["bin"]),
                    yolo_short=agent_short(agent),
                    agent_cmd=agent_cmd,
                    checks=", ".join(prep.get("failing_checks") or []) or "no failing checks",
                    shell=shlex.quote(USER_SHELL),
                )
                argv = ["bash", "-c", wrapper]
                sess = spawn_pty(argv, cwd=str(REPO_ROOT), env_extra=env_extra,
                                 label=f"{agent['id']} fix-ci · PR #{pr}", rows=rows, cols=cols)
                return self._send_json({
                    "sid": sess["sid"],
                    "label": sess["label"],
                    "cwd": sess["cwd"],
                    "pr": pr,
                    "pr_url": prep.get("url"),
                    "branch": prep.get("branch"),
                    "agent": agent["id"],
                    "model": agent.get("model"),
                    "prompt_file": prompt_file,
                })

            if kind == "propose-issue":
                slug_hint = (payload.get("slug") or "").strip()
                prep = prepare_proposal(slug_hint)
                if prep.get("error"):
                    return self._send_json(prep, 400)
                slug = prep["slug"]
                prompt_file = prep["prompt_file"]
                draft_file  = prep["draft_file"]

                agent = resolve_agent(
                    payload.get("agent"),
                    override_model=payload.get("model"),
                    override_bin=payload.get("bin"),
                    override_yolo=payload.get("yolo_flag"),
                )
                agent_cmd = build_agent_cmd(agent, f"$(cat {shlex.quote(prompt_file)})")

                env_extra = {
                    "DRAFT_FILE": draft_file,
                    "PROPOSAL_SLUG": slug,
                    "PROMPT_FILE": prompt_file,
                    "PS1": "\\[\\e[32m\\]propose·" + slug + "\\[\\e[0m\\]:\\W$ ",
                }

                # Same shape as the issue terminal — interactive agent,
                # then drop to shell with the gh create command pre-printed.
                wrapper = (
                    'echo "──── starting {bin} ({yolo_short}) — propose new issue ────"; '
                    'echo "      agent:  {agent_label}"; '
                    'echo "      model:  {model}"; '
                    'echo "      slug:   {slug}"; '
                    'echo "      draft:  $DRAFT_FILE  (agent will fill this in)"; '
                    'echo "      prompt: $PROMPT_FILE"; '
                    'echo "────"; '
                    '{agent_cmd}; '
                    'ec=$?; '
                    'echo; '
                    'echo "──── {bin} exited (code $ec) — dropping to shell ────"; '
                    'if [ -s "$DRAFT_FILE" ]; then '
                        'echo "  draft saved to $DRAFT_FILE — preview:"; '
                        'echo "  ────"; '
                        'head -20 "$DRAFT_FILE" | sed \'s/^/  | /\'; '
                        'echo "  ────"; '
                        'title=$(head -1 "$DRAFT_FILE" | sed \'s/^# *//\'); '
                        'echo "  to create the issue:"; '
                        'echo "    gh issue create --title \\"$title\\" --body-file $DRAFT_FILE --label agent-friendly --label claim-next"; '
                    'else '
                        'echo "  $DRAFT_FILE is empty — agent did not produce a draft."; '
                    'fi; '
                    'exec {shell} -i'
                ).format(
                    bin=shlex.quote(agent["bin"]),
                    yolo_short=agent_short(agent),
                    slug=slug,
                    agent_label=agent["label"],
                    model=agent.get("model") or "(agent default)",
                    agent_cmd=agent_cmd,
                    shell=shlex.quote(USER_SHELL),
                )
                argv = ["bash", "-c", wrapper]
                sess = spawn_pty(argv, cwd=str(REPO_ROOT),
                                 env_extra=env_extra,
                                 label=f"propose · {slug}",
                                 rows=rows, cols=cols)
                return self._send_json({
                    "sid": sess["sid"],
                    "label": sess["label"],
                    "cwd": sess["cwd"],
                    "slug": slug,
                    "agent": agent["id"],
                    "model": agent.get("model"),
                    "prompt_file": prompt_file,
                    "draft_file": draft_file,
                })

            if kind == "issue-shell":
                try:
                    issue = int(payload.get("issue"))
                except (TypeError, ValueError):
                    return self._send_json({"error": "issue must be int"}, 400)
                existing = live_issue_pty(issue)
                if existing:
                    meta = existing.get("meta") or {}
                    agent = resolve_agent(
                        payload.get("agent"),
                        override_model=payload.get("model"),
                        override_bin=payload.get("bin"),
                        override_yolo=payload.get("yolo_flag"),
                    )
                    return self._send_json({
                        "sid": existing["sid"],
                        "label": existing.get("label") or f"#{issue}",
                        "cwd": existing.get("cwd") or "",
                        "issue": issue,
                        "branch": meta.get("branch"),
                        "prompt_file": meta.get("prompt_file"),
                        "agent": agent["id"],
                        "model": agent.get("model"),
                        "reused": True,
                    })
                prep = prepare_issue_worktree(issue)
                if prep.get("error"):
                    return self._send_json(prep, 400)
                wt = Path(prep["worktree"])
                prompt_file = prep.get("prompt_file") or ""
                if not prompt_file or not Path(prompt_file).exists():
                    return self._send_json({"error": "prompt file missing — worktree prep incomplete"}, 500)

                agent = resolve_agent(
                    payload.get("agent"),
                    override_model=payload.get("model"),
                    override_bin=payload.get("bin"),
                    override_yolo=payload.get("yolo_flag"),
                )
                agent_cmd = build_agent_cmd(agent, '$(cat "$AGENT_PROMPT_FILE")')

                env_extra = {
                    "AGENT_ISSUE": str(issue),
                    "AGENT_BRANCH": prep.get("branch", ""),
                    "AGENT_PROMPT_FILE": prompt_file,
                    "PS1": "\\[\\e[33m\\]#" + str(issue) + "\\[\\e[0m\\]:\\W$ ",
                }

                # Spawn the agent directly under the PTY. Wrapped in bash so:
                #   1) we print a banner the user can see in the terminal
                #   2) when the agent exits we drop into an interactive shell in
                #      the worktree instead of closing the session
                # The prompt is read via $(cat …) so we don't have to worry
                # about shell quoting on multi-line markdown.
                wrapper = (
                    'echo "──── starting {bin} ({yolo_short}) on issue #{issue} ────"; '
                    'echo "      agent:  {agent_label}"; '
                    'echo "      model:  {model}"; '
                    'echo "      branch: $AGENT_BRANCH"; '
                    'echo "      prompt: $AGENT_PROMPT_FILE"; '
                    'echo "────"; '
                    '{agent_cmd}; '
                    'ec=$?; '
                    'echo; '
                    'echo "──── {bin} exited (code $ec) — dropping to shell ────"; '
                    'exec {shell} -i'
                ).format(
                    bin=shlex.quote(agent["bin"]),
                    yolo_short=agent_short(agent),
                    issue=issue,
                    agent_label=agent["label"],
                    model=agent.get("model") or "(agent default)",
                    agent_cmd=agent_cmd,
                    shell=shlex.quote(USER_SHELL),
                )
                argv = ["bash", "-c", wrapper]
                sess = spawn_pty(
                    argv,
                    cwd=str(wt),
                    env_extra=env_extra,
                    label=f"{agent['id']} #{issue} · {wt.name}",
                    rows=rows,
                    cols=cols,
                    meta={
                        "issue": issue,
                        "kind": "issue",
                        "branch": prep.get("branch", ""),
                        "worktree": str(wt),
                        "prompt_file": prompt_file,
                    },
                )
                return self._send_json({
                    "sid": sess["sid"],
                    "label": sess["label"],
                    "cwd": sess["cwd"],
                    "issue": issue,
                    "branch": prep.get("branch"),
                    "prompt_file": prompt_file,
                    "agent": agent["id"],
                    "model": agent.get("model"),
                    "reused": False,
                })
            if kind == "issue-review":
                try:
                    issue = int(payload.get("issue"))
                except (TypeError, ValueError):
                    return self._send_json({"error": "issue must be int"}, 400)
                prep = prepare_issue_review(issue)
                if prep.get("error"):
                    return self._send_json(prep, 400)
                prompt_file = prep["prompt_file"]
                review_out = STATE_DIR / f"issue-review-{issue}.md"
                review_url_file = STATE_DIR / f"issue-review-{issue}.url"
                review_url_file.unlink(missing_ok=True)

                agent = resolve_agent(
                    payload.get("agent"),
                    override_model=payload.get("model"),
                    override_bin=payload.get("bin"),
                    override_yolo=payload.get("yolo_flag"),
                )
                agent_cmd = build_agent_cmd(agent, f"$(cat {shlex.quote(prompt_file)})")

                env_extra = {
                    "ISSUE_NUMBER": str(issue),
                    "REVIEW_OUT": str(review_out),
                    "REVIEW_URL_FILE": str(review_url_file),
                    "PROMPT_FILE": prompt_file,
                    "PS1": "\\[\\e[35m\\]review·issue#" + str(issue) + "\\[\\e[0m\\]:\\W$ ",
                }
                wrapper = (
                    'touch $REVIEW_OUT; '
                    'echo "──── starting {bin} ({yolo_short}) review of issue #{issue} ────"; '
                    'echo "      agent:  {agent_label}"; '
                    'echo "      model:  {model}"; '
                    'echo "      prompt: $PROMPT_FILE"; '
                    'echo "      out:    $REVIEW_OUT  (agent writes verdict here)"; '
                    'echo "────"; '
                    '{agent_cmd}; '
                    'ec=$?; '
                    'echo; '
                    'echo "──── {bin} exited (code $ec) ────"; '
                    'if [ -s "$REVIEW_OUT" ]; then '
                        'echo "  $REVIEW_OUT has $(wc -l < $REVIEW_OUT) lines — posting to issue #{issue}…"; '
                        'url=$(gh issue comment {issue} -F $REVIEW_OUT 2>&1); '
                        'echo "  $url"; '
                        'echo "$url" | grep -Eo \'https://github.com/[^ ]+\' | head -1 > $REVIEW_URL_FILE; '
                        'echo "  comment url saved to $REVIEW_URL_FILE"; '
                    'else '
                        'echo "  $REVIEW_OUT is empty — agent did not produce a verdict file."; '
                        'echo "  to post manually: gh issue comment {issue} -F $REVIEW_OUT (after writing it)"; '
                    'fi; '
                    'echo; '
                    'exec {shell} -i'
                ).format(
                    issue=issue,
                    agent_label=agent["label"],
                    model=agent.get("model") or "(agent default)",
                    bin=shlex.quote(agent["bin"]),
                    yolo_short=agent_short(agent),
                    agent_cmd=agent_cmd,
                    shell=shlex.quote(USER_SHELL),
                )
                argv = ["bash", "-c", wrapper]
                sess = spawn_pty(argv, cwd=str(REPO_ROOT),
                                 env_extra=env_extra,
                                 label=f"{agent['id']} review · issue #{issue}",
                                 rows=rows, cols=cols)
                return self._send_json({
                    "sid": sess["sid"],
                    "label": sess["label"],
                    "cwd": sess["cwd"],
                    "issue": issue,
                    "issue_url": prep.get("url"),
                    "agent": agent["id"],
                    "model": agent.get("model"),
                    "prompt_file": prompt_file,
                    "review_out": str(review_out),
                    "review_url_file": str(review_url_file),
                })
            return self._send_json({"error": f"unknown kind: {kind}"}, 400)

        if u.path == "/api/pty/input":
            sid = payload.get("sid", "")
            data = payload.get("data", "")
            if not isinstance(data, str):
                return self._send_json({"error": "data must be string"}, 400)
            ok = pty_write(sid, data.encode("utf-8", errors="replace"))
            return self._send_json({"ok": ok})

        if u.path == "/api/pty/resize":
            sid = payload.get("sid", "")
            try:
                rows = int(payload.get("rows"))
                cols = int(payload.get("cols"))
            except (TypeError, ValueError):
                return self._send_json({"error": "rows/cols must be int"}, 400)
            ok = pty_resize(sid, rows, cols)
            return self._send_json({"ok": ok})

        if u.path == "/api/pty/close":
            sid = payload.get("sid", "")
            ok = kill_pty(sid)
            return self._send_json({"ok": ok})

        if u.path == "/api/pty/delete":
            sid = payload.get("sid", "")
            ok = delete_pty(sid)
            return self._send_json({"ok": ok})

        if u.path == "/api/worktree/remove":
            name = (payload.get("name") or "").strip()
            result = remove_worktree(name)
            return self._send_json(result, 200 if result.get("removed") else 400)

        if u.path == "/api/state/cleanup":
            try:
                stale_days = int(payload.get("stale_days", 7))
            except (TypeError, ValueError):
                return self._send_json({"error": "stale_days must be int"}, 400)
            dry = bool(payload.get("dry_run", False))
            cutoff = time.time() - max(0, stale_days) * 86400
            # Sanctioned prefixes — never touch .gitignore or unknown files.
            CLEAN_PREFIXES = (
                "implementer-", "orchestrator-", "review-spawn-",
                "review-prompt-", "review-",
                "pr-", "issue-", "prompt-",
                "proposal-", "proposal-prompt-",
            )
            removed, kept = [], []
            total_freed = 0
            for p in sorted(STATE_DIR.iterdir()):
                if not p.is_file():
                    continue
                if not any(p.name.startswith(pfx) for pfx in CLEAN_PREFIXES):
                    continue
                try:
                    st = p.stat()
                except OSError:
                    continue
                if st.st_mtime < cutoff:
                    if not dry:
                        try:
                            p.unlink()
                        except OSError as e:
                            kept.append({"name": p.name, "reason": str(e)})
                            continue
                    removed.append({"name": p.name, "size": st.st_size,
                                    "age_days": round((time.time() - st.st_mtime) / 86400, 1)})
                    total_freed += st.st_size
                else:
                    kept.append({"name": p.name, "size": st.st_size,
                                 "age_days": round((time.time() - st.st_mtime) / 86400, 1)})
            return self._send_json({
                "dry_run": dry,
                "stale_days": stale_days,
                "removed": removed,
                "kept_count": len(kept),
                "freed_bytes": total_freed,
            })

        self.send_response(404)
        self.end_headers()



def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 7777
    bind = ("127.0.0.1", port)
    print(f"gitswarm dashboard: http://localhost:{port}", flush=True)
    print(f"  state dir:   {STATE_DIR}", flush=True)
    print(f"  worktrees:   {WORKTREES_DIR}", flush=True)
    http.server.ThreadingHTTPServer(bind, Handler).serve_forever()


if __name__ == "__main__":
    main()
