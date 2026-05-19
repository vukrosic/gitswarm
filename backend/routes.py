"""Route dispatch table for GET and POST handlers."""
from urllib.parse import unquote


_AGENT_GRID = {"active": False, "sessions": [], "agent": ""}


def _query_value(qs, name, default=""):
    value = qs.get(name, default)
    if isinstance(value, list):
        return value[0] if value else default
    return value


def dispatch_get(handler, u, qs, send_json_fn):
    path = u.path

    if path == "/api/issue":
        return _handle_issue_meta(handler, qs, send_json_fn)
    if path == "/api/pr":
        return _handle_pr_meta(handler, qs, send_json_fn)
    if path == "/api/pr/diff":
        return _handle_pr_diff(handler, qs, send_json_fn)
    if path == "/api/agents":
        return _handle_agents(handler, send_json_fn)
    if path == "/api/files":
        from github import list_state_files
        return send_json_fn(handler, {"files": list_state_files()})
    if path == "/api/worktrees":
        from github import list_worktrees, list_running_orchestrators
        return send_json_fn(handler, {"worktrees": list_worktrees(), "running": list_running_orchestrators()})
    if path == "/api/issues":
        from github import list_issues
        return send_json_fn(handler, {"issues": list_issues()})
    if path == "/api/milestones":
        from github import list_milestones
        return send_json_fn(handler, {"milestones": list_milestones()})
    if path == "/api/notifications":
        from github import list_notifications
        all_read = qs.get("all_read", ["false"])[0] == "true"
        reason = qs.get("reason", ["owner"])[0]
        return send_json_fn(handler, {"notifications": list_notifications(all_read=all_read, reason=reason)})
    if path == "/api/prs":
        from github import list_prs
        return send_json_fn(handler, {"prs": list_prs()})
    if path == "/api/pty/list":
        from github import reap_dead_ptys, list_ptys
        reap_dead_ptys()
        return send_json_fn(handler, {"sessions": list_ptys()})
    if path == "/api/pty/stream":
        return _handle_pty_stream(handler, qs, send_json_fn)
    if path == "/api/file":
        return _handle_file_read(handler, qs, send_json_fn)
    if path == "/api/agent-grid/status":
        return _handle_agent_grid_status(handler, send_json_fn)
    # Fall-through to 404
    handler.send_response(404)
    handler.end_headers()
    return None


def _handle_issue_meta(handler, qs, send_json_fn):
    from github import fetch_issue_meta, gh_error
    try:
        num = int(_query_value(qs, "num"))
    except ValueError:
        return send_json_fn(handler, {"error": "bad num"}, 400)
    if not (1 <= num <= 9999):
        return send_json_fn(handler, {"error": "bad num"}, 400)
    try:
        return send_json_fn(handler, fetch_issue_meta(num))
    except Exception as e:
        return send_json_fn(handler, {"error": gh_error(e)}, 500)


def _handle_pr_meta(handler, qs, send_json_fn):
    from github import fetch_pr_meta, gh_error
    try:
        num = int(_query_value(qs, "num"))
    except ValueError:
        return send_json_fn(handler, {"error": "bad num"}, 400)
    if not (1 <= num <= 9999):
        return send_json_fn(handler, {"error": "bad num"}, 400)
    try:
        return send_json_fn(handler, fetch_pr_meta(num))
    except Exception as e:
        return send_json_fn(handler, {"error": gh_error(e)}, 500)


def _handle_pr_diff(handler, qs, send_json_fn):
    from github import fetch_pr_diff, gh_error
    try:
        num = int(_query_value(qs, "num"))
    except ValueError:
        return send_json_fn(handler, {"error": "bad num"}, 400)
    if not (1 <= num <= 9999):
        return send_json_fn(handler, {"error": "bad num"}, 400)
    try:
        return send_json_fn(handler, {"number": num, "diff": fetch_pr_diff(num)})
    except Exception as e:
        return send_json_fn(handler, {"error": gh_error(e)}, 500)


def _handle_agents(handler, send_json_fn):
    from backend.reload import frontend_mtime_detail
    from github import AGENTS, DEFAULT_AGENT
    import shutil
    out = []
    for aid, cfg in AGENTS.items():
        out.append({
            "id": aid,
            "label": cfg["label"],
            "bin": cfg["bin"],
            "model": cfg.get("model") or "",
            "available": shutil.which(cfg["bin"]) is not None,
        })
    mtime, newest = frontend_mtime_detail()
    return send_json_fn(handler, {"agents": out, "default": DEFAULT_AGENT,
                                  "code_mtime": mtime,
                                  "code_mtime_path": newest})


def _handle_pty_stream(handler, qs, send_json_fn):
    from github import pty_read
    sid = unquote(_query_value(qs, "sid"))
    try:
        offset = max(0, int(_query_value(qs, "offset", "0") or 0))
    except ValueError:
        return send_json_fn(handler, {"error": "bad offset"}, 400)
    try:
        timeout = max(1, min(25, int(_query_value(qs, "timeout", "15") or 15)))
    except ValueError:
        timeout = 15
    res = pty_read(sid, offset, timeout=timeout)
    if res is None:
        return send_json_fn(handler, {"error": "unknown sid"}, 404)
    data, logical_len, alive, drop, reset = res
    handler.send_response(200)
    handler.send_header("Content-Type", "application/octet-stream")
    handler.send_header("X-Offset", str(logical_len))
    handler.send_header("X-Alive", "1" if alive else "0")
    handler.send_header("X-Drop", str(drop))
    handler.send_header("X-Reset", "1" if reset else "0")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)
    return None


def _handle_file_read(handler, qs, send_json_fn):
    from github import STATE_DIR
    name = unquote(_query_value(qs, "name"))
    try:
        offset = max(0, int(_query_value(qs, "offset", "0") or 0))
    except ValueError:
        return send_json_fn(handler, {"error": "bad offset"}, 400)
    if not name or "/" in name or ".." in name:
        return send_json_fn(handler, {"error": "bad name"}, 400)
    fp = STATE_DIR / name
    if not fp.exists() or not fp.is_file():
        return send_json_fn(handler, {"error": "not found"}, 404)
    size = fp.stat().st_size
    if offset >= size:
        body = b""
    else:
        with fp.open("rb") as fh:
            fh.seek(offset)
            data = fh.read()
        if offset == 0 and len(data) > 2_000_000:
            data = b"[\xe2\x80\xa6truncated to last 2MB\xe2\x80\xa6]\n" + data[-2_000_000:]
        body = data
    handler.send_response(200)
    handler.send_header("Content-Type", "text/plain; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("X-Total-Size", str(size))
    handler.end_headers()
    handler.wfile.write(body)
    return None


def dispatch_post(handler, u, payload, send_json_fn):
    path = u.path
    if path == "/api/launch":
        return _handle_launch(handler, payload, send_json_fn)
    if path == "/api/review":
        return _handle_review(handler, payload, send_json_fn)
    if path == "/api/merge":
        return _handle_merge(handler, payload, send_json_fn)
    if path == "/api/pty/new":
        return _handle_pty_new(handler, payload, send_json_fn)
    if path == "/api/pty/input":
        return _handle_pty_input(handler, payload, send_json_fn)
    if path == "/api/pty/resize":
        return _handle_pty_resize(handler, payload, send_json_fn)
    if path == "/api/pty/close":
        return _handle_pty_close(handler, payload, send_json_fn)
    if path == "/api/pty/delete":
        return _handle_pty_delete(handler, payload, send_json_fn)
    if path == "/api/pty/rename":
        return _handle_pty_rename(handler, payload, send_json_fn)
    if path == "/api/worktree/remove":
        return _handle_worktree_remove(handler, payload, send_json_fn)
    if path == "/api/state/cleanup":
        return _handle_state_cleanup(handler, payload, send_json_fn)
    if path == "/api/agent-grid/launch":
        return _handle_agent_grid_launch(handler, payload, send_json_fn)
    if path == "/api/agent-grid/close":
        return _handle_agent_grid_close(handler, payload, send_json_fn)
    # Issue CRUD — delegate to github
    if path in ("/api/issue/update", "/api/issue/delete", "/api/issue/create"):
        return _handle_issue(handler, path, payload, send_json_fn)
    # Fall-through to 404
    handler.send_response(404)
    handler.end_headers()
    return None


def _handle_launch(handler, payload, send_json_fn):
    from github import launch_orchestrator
    try:
        issue = int(payload.get("issue"))
    except (TypeError, ValueError):
        return send_json_fn(handler, {"error": "issue must be int"}, 400)
    mode = payload.get("mode", "watch")
    result = launch_orchestrator(issue, mode)
    return send_json_fn(handler, result, 200 if result.get("started") else 400)


def _handle_review(handler, payload, send_json_fn):
    from github import spawn_review
    try:
        pr = int(payload.get("pr"))
    except (TypeError, ValueError):
        return send_json_fn(handler, {"error": "pr must be int"}, 400)
    result = spawn_review(pr)
    return send_json_fn(handler, result, 200 if result.get("started") else 400)


def _handle_merge(handler, payload, send_json_fn):
    from github import merge_pr
    try:
        pr = int(payload.get("pr"))
    except (TypeError, ValueError):
        return send_json_fn(handler, {"error": "pr must be int"}, 400)
    strategy = payload.get("strategy", "squash")
    result = merge_pr(pr, strategy)
    return send_json_fn(handler, result, 200 if result.get("merged") else 400)


def _handle_pty_input(handler, payload, send_json_fn):
    from github import pty_write
    sid = payload.get("sid", "")
    data = payload.get("data", "")
    if not isinstance(data, str):
        return send_json_fn(handler, {"error": "data must be string"}, 400)
    ok = pty_write(sid, data.encode("utf-8", errors="replace"))
    return send_json_fn(handler, {"ok": ok})


def _handle_pty_resize(handler, payload, send_json_fn):
    from github import pty_resize
    sid = payload.get("sid", "")
    try:
        rows = int(payload.get("rows"))
        cols = int(payload.get("cols"))
    except (TypeError, ValueError):
        return send_json_fn(handler, {"error": "rows/cols must be int"}, 400)
    ok = pty_resize(sid, rows, cols)
    return send_json_fn(handler, {"ok": ok})


def _handle_pty_close(handler, payload, send_json_fn):
    from github import kill_pty
    sid = payload.get("sid", "")
    ok = kill_pty(sid)
    return send_json_fn(handler, {"ok": ok})


def _handle_pty_delete(handler, payload, send_json_fn):
    from github import delete_pty
    sid = payload.get("sid", "")
    ok = delete_pty(sid)
    return send_json_fn(handler, {"ok": ok})


def _handle_pty_rename(handler, payload, send_json_fn):
    from github import pty_rename
    sid = payload.get("sid", "")
    label = payload.get("label", "")
    if not sid:
        return send_json_fn(handler, {"error": "sid is required"}, 400)
    ok = pty_rename(sid, label)
    return send_json_fn(handler, {"ok": ok})


def _handle_worktree_remove(handler, payload, send_json_fn):
    from github import remove_worktree
    name = (payload.get("name") or "").strip()
    result = remove_worktree(name)
    return send_json_fn(handler, result, 200 if result.get("removed") else 400)


def _handle_state_cleanup(handler, payload, send_json_fn):
    from github import STATE_DIR
    import time
    try:
        stale_days = int(payload.get("stale_days", 7))
    except (TypeError, ValueError):
        return send_json_fn(handler, {"error": "stale_days must be int"}, 400)
    dry = bool(payload.get("dry_run", False))
    cutoff = time.time() - max(0, stale_days) * 86400
    CLEAN_PREFIXES = (
        "implementer-", "orchestrator-", "review-spawn-",
        "review-prompt-", "review-",
        "pr-", "issue-", "prompt-",
        "propose-", "proposal-prompt-",
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
    return send_json_fn(handler, {
        "dry_run": dry,
        "stale_days": stale_days,
        "removed": removed,
        "kept_count": len(kept),
        "freed_bytes": total_freed,
    })


def _handle_issue(handler, path, payload, send_json_fn):
    from github import update_issue, close_issue, create_issue, gh_error
    if path == "/api/issue/update":
        try:
            issue = int(payload.get("issue"))
        except (TypeError, ValueError):
            return send_json_fn(handler, {"error": "issue must be int"}, 400)
        title = payload.get("title")
        body_text = payload.get("body")
        result = update_issue(issue, title=title, body=body_text)
        status = 200 if not result.get("error") else 400
        return send_json_fn(handler, result, status)
    if path == "/api/issue/delete":
        try:
            issue = int(payload.get("issue"))
        except (TypeError, ValueError):
            return send_json_fn(handler, {"error": "issue must be int"}, 400)
        result = close_issue(issue)
        status = 200 if not result.get("error") else 400
        return send_json_fn(handler, result, status)
    if path == "/api/issue/create":
        title = payload.get("title", "")
        body_text = payload.get("body", "")
        result = create_issue(title, body=body_text)
        status = 200 if not result.get("error") else 400
        return send_json_fn(handler, result, status)
    return send_json_fn(handler, {"error": "unhandled"}, 404)


def _handle_pty_new(handler, payload, send_json_fn):
    from github import (
        spawn_shell_session, spawn_pty, pty_resize,
        resolve_agent, build_agent_cmd, agent_short,
        USER_SHELL, REPO_ROOT, STATE_DIR,
        prepare_issue_worktree, live_issue_pty,
        prepare_pr_review, prepare_merge, prepare_ci_fix,
        prepare_proposal, prepare_issue_review,
        gh_error,
    )
    import shlex
    from pathlib import Path
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
        try:
            cwd_path.relative_to(REPO_ROOT.resolve())
        except ValueError:
            return send_json_fn(handler, {"error": "cwd must be inside repo"}, 400)
        env_extra = {"PS1": "\\[\\e[36m\\]agent\\[\\e[0m\\]:\\W$ "}
        res = spawn_shell_session(cwd_path, env_extra=env_extra)
        if res.get("error"):
            return send_json_fn(handler, res, 400)
        pty_resize(res["sid"], rows, cols)
        return send_json_fn(handler, res)

    if kind == "agent-shell":
        return _handle_agent_shell(handler, payload, rows, cols, send_json_fn)
    if kind == "agent-prompt":
        return _handle_agent_prompt(handler, payload, rows, cols, send_json_fn)
    if kind == "pr-review":
        return _handle_pr_review(handler, payload, rows, cols, send_json_fn)
    if kind == "merge-pr":
        return _handle_merge_pr(handler, payload, rows, cols, send_json_fn)
    if kind == "ci-fix":
        return _handle_ci_fix(handler, payload, rows, cols, send_json_fn)
    if kind == "propose-issue":
        return _handle_propose_issue(handler, payload, rows, cols, send_json_fn)
    if kind == "issue-shell":
        return _handle_issue_shell(handler, payload, rows, cols, send_json_fn)
    if kind == "issue-review":
        return _handle_issue_review(handler, payload, rows, cols, send_json_fn)

    return send_json_fn(handler, {"error": f"unknown kind: {kind}"}, 400)


def _agent_wrapper(env_extra, agent, cwd_path, prompt_file, issue_num, prep,
                   shell_wrapper_fn, rows, cols, label, meta=None):
    from github import spawn_pty, USER_SHELL, REPO_ROOT, agent_short, build_agent_cmd
    import shlex
    wrapper = shell_wrapper_fn(
        bin=shlex.quote(agent["bin"]),
        yolo_short=agent_short(agent),
        agent_label=agent["label"],
        model=agent.get("model") or "(agent default)",
        agent_cmd=build_agent_cmd(agent, f"$(cat {shlex.quote(prompt_file)})"),
        shell=shlex.quote(USER_SHELL),
    )
    argv = ["bash", "-c", wrapper]
    sess = spawn_pty(
        argv,
        cwd=str(cwd_path),
        env_extra=env_extra,
        label=label,
        rows=rows,
        cols=cols,
        meta=meta,
    )
    return sess


def _handle_agent_shell(handler, payload, rows, cols, send_json_fn):
    from github import spawn_pty, resolve_agent, build_agent_cmd, agent_short, USER_SHELL, REPO_ROOT
    import shlex
    from pathlib import Path
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
        return send_json_fn(handler, {"error": "cwd must be inside repo"}, 400)

    agent = resolve_agent(
        payload.get("agent"),
        override_model=payload.get("model"),
        override_bin=payload.get("bin"),
        override_yolo=payload.get("yolo_flag"),
    )
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
    return send_json_fn(handler, {
        "sid": sess["sid"],
        "label": sess["label"],
        "cwd": sess["cwd"],
        "agent": agent["id"],
        "model": agent.get("model"),
    })


def _handle_agent_prompt(handler, payload, rows, cols, send_json_fn):
    from github import (
        spawn_pty, resolve_agent, build_agent_cmd, agent_short,
        USER_SHELL, REPO_ROOT, STATE_DIR, prepare_issue_worktree,
        live_issue_pty, gh_error,
    )
    import shlex, re, secrets
    from pathlib import Path

    issue_num = None
    if payload.get("issue") not in (None, "", 0, "0"):
        try:
            issue_num = int(payload.get("issue"))
        except (TypeError, ValueError):
            return send_json_fn(handler, {"error": "issue must be int"}, 400)
        existing = live_issue_pty(issue_num)
        if existing:
            meta = existing.get("meta") or {}
            agent = resolve_agent(
                payload.get("agent"),
                override_model=payload.get("model"),
                override_bin=payload.get("bin"),
                override_yolo=payload.get("yolo_flag"),
            )
            return send_json_fn(handler, {
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
        return send_json_fn(handler, {"error": "prompt is required"}, 400)

    prep = None
    cwd_path = None
    if issue_num is not None and not cwd_in:
        prep = prepare_issue_worktree(issue_num)
        if prep.get("error"):
            return send_json_fn(handler, prep, 400)
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
            return send_json_fn(handler, {"error": "cwd must be inside repo"}, 400)

    agent = resolve_agent(
        payload.get("agent"),
        override_model=payload.get("model"),
        override_bin=payload.get("bin"),
        override_yolo=payload.get("yolo_flag"),
    )
    slug = re.sub(r"[^a-z0-9]+", "-", (payload.get("label") or prompt).lower()).strip("-")[:40] or "prompt"
    prompt_file = STATE_DIR / f"prompt-{secrets.token_hex(4)}-{slug}.md"
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
            env_extra["AGENT_PROMPT_FILE"] = str(prompt_file)
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
        label=f"{agent['id']} #{issue_num} · {slug}" if issue_num is not None else f"{agent['id']} · {slug}",
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
    return send_json_fn(handler, {
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


def _handle_pr_review(handler, payload, rows, cols, send_json_fn):
    from github import (
        spawn_pty, resolve_agent, build_agent_cmd, agent_short,
        USER_SHELL, REPO_ROOT, STATE_DIR, prepare_pr_review,
        gh_error,
    )
    import shlex
    try:
        pr = int(payload.get("pr"))
    except (TypeError, ValueError):
        return send_json_fn(handler, {"error": "pr must be int"}, 400)
    prep = prepare_pr_review(pr)
    if prep.get("error"):
        return send_json_fn(handler, prep, 400)
    prompt_file = prep["prompt_file"]
    review_out = STATE_DIR / f"review-{pr}.md"

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
    return send_json_fn(handler, {
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


def _handle_merge_pr(handler, payload, rows, cols, send_json_fn):
    from github import (
        spawn_pty, resolve_agent, build_agent_cmd, agent_short,
        USER_SHELL, REPO_ROOT, prepare_merge, github_repo_slug,
        gh_error,
    )
    import shlex
    try:
        pr = int(payload.get("pr"))
    except (TypeError, ValueError):
        return send_json_fn(handler, {"error": "pr must be int"}, 400)
    prep = prepare_merge(pr)
    if prep.get("error"):
        return send_json_fn(handler, prep, 400)
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
        'echo "  PR state: $(gh api {api_path_q} --jq \'.state + (if .merged_at then " (merged " + .merged_at + ")" else "" end)\' 2>/dev/null)"; '
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
    return send_json_fn(handler, {
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


def _handle_ci_fix(handler, payload, rows, cols, send_json_fn):
    from github import (
        spawn_pty, resolve_agent, build_agent_cmd, agent_short,
        USER_SHELL, REPO_ROOT, prepare_ci_fix,
    )
    import shlex
    try:
        pr = int(payload.get("pr"))
    except (TypeError, ValueError):
        return send_json_fn(handler, {"error": "pr must be int"}, 400)
    prep = prepare_ci_fix(pr)
    if prep.get("error"):
        return send_json_fn(handler, prep, 400)
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
    return send_json_fn(handler, {
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


def _handle_propose_issue(handler, payload, rows, cols, send_json_fn):
    from github import (
        spawn_pty, resolve_agent, build_agent_cmd, agent_short,
        USER_SHELL, REPO_ROOT, STATE_DIR, prepare_proposal,
    )
    import shlex
    slug_hint = (payload.get("slug") or "").strip()
    prep = prepare_proposal(slug_hint)
    if prep.get("error"):
        return send_json_fn(handler, prep, 400)
    slug = prep["slug"]
    prompt_file = prep["prompt_file"]
    draft_file = prep["draft_file"]

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
    return send_json_fn(handler, {
        "sid": sess["sid"],
        "label": sess["label"],
        "cwd": sess["cwd"],
        "slug": slug,
        "agent": agent["id"],
        "model": agent.get("model"),
        "prompt_file": prompt_file,
        "draft_file": draft_file,
    })


def _handle_issue_shell(handler, payload, rows, cols, send_json_fn):
    from github import (
        spawn_pty, resolve_agent, build_agent_cmd, agent_short,
        USER_SHELL, REPO_ROOT, STATE_DIR, prepare_issue_worktree,
        live_issue_pty, gh_error,
    )
    import shlex
    from pathlib import Path
    try:
        issue = int(payload.get("issue"))
    except (TypeError, ValueError):
        return send_json_fn(handler, {"error": "issue must be int"}, 400)
    existing = live_issue_pty(issue)
    if existing:
        meta = existing.get("meta") or {}
        agent = resolve_agent(
            payload.get("agent"),
            override_model=payload.get("model"),
            override_bin=payload.get("bin"),
            override_yolo=payload.get("yolo_flag"),
        )
        return send_json_fn(handler, {
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
        return send_json_fn(handler, prep, 400)
    wt = Path(prep["worktree"])
    prompt_file = prep.get("prompt_file") or ""
    if not prompt_file or not Path(prompt_file).exists():
        return send_json_fn(handler, {"error": "prompt file missing — worktree prep incomplete"}, 500)

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
    return send_json_fn(handler, {
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


def _handle_issue_review(handler, payload, rows, cols, send_json_fn):
    from github import (
        spawn_pty, resolve_agent, build_agent_cmd, agent_short,
        USER_SHELL, REPO_ROOT, STATE_DIR, prepare_issue_review,
        gh_error, extract_issue_review_comment,
    )
    import shlex
    try:
        issue = int(payload.get("issue"))
    except (TypeError, ValueError):
        return send_json_fn(handler, {"error": "issue must be int"}, 400)
    prep = prepare_issue_review(issue)
    if prep.get("error"):
        return send_json_fn(handler, prep, 400)
    prompt_file = prep["prompt_file"]
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
        "REVIEW_URL_FILE": str(review_url_file),
        "PROMPT_FILE": prompt_file,
        "PS1": "\\[\\e[35m\\]review·issue#" + str(issue) + "\\[\\e[0m\\]:\\W$ ",
    }
    wrapper = (
        'set -o pipefail; '
        'echo "──── starting {bin} ({yolo_short}) review of issue #{issue} ────"; '
        'echo "      agent:  {agent_label}"; '
        'echo "      model:  {model}"; '
        'echo "      prompt: $PROMPT_FILE"; '
        'echo "      verdict: will auto-post from terminal output"; '
        'echo "────"; '
        'review_text="$({agent_cmd} 2>&1 | tee /dev/tty)"; '
        'ec=$?; '
        'set +o pipefail; '
        'echo; '
        'echo "──── {bin} exited (code $ec) ────"; '
        'comment="$(printf %s "$review_text" | python3 -c \'import sys; from github import extract_issue_review_comment; sys.stdout.write(extract_issue_review_comment(sys.stdin.read()))\')"; '
        'if [ -n "$comment" ]; then '
            'echo "  posting verdict to issue #{issue}…"; '
            'url=$(printf %s "$comment" | gh issue comment {issue} --body-file - 2>&1); '
            'echo "  $url"; '
            'echo "$url" | grep -Eo \'https://github.com/[^ ]+\' | head -1 > $REVIEW_URL_FILE; '
            'echo "  comment url saved to $REVIEW_URL_FILE"; '
        'else '
            'echo "  no verdict block found in agent output — nothing posted."; '
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
    return send_json_fn(handler, {
        "sid": sess["sid"],
        "label": sess["label"],
        "cwd": sess["cwd"],
        "issue": issue,
        "issue_url": prep.get("url"),
        "agent": agent["id"],
        "model": agent.get("model"),
        "prompt_file": prompt_file,
        "review_url_file": str(review_url_file),
    })


def _handle_agent_grid_status(handler, send_json_fn):
    from github import list_ptys, reap_dead_ptys
    reap_dead_ptys()
    grid_sessions = [s for s in list_ptys() if s.get("kind") == "agent-grid-cell"]
    return send_json_fn(handler, {
        "active": _AGENT_GRID["active"],
        "sessions": list_ptys(),
        "gridSessions": grid_sessions,
        "agent": _AGENT_GRID.get("agent", ""),
    })


def _handle_agent_grid_launch(handler, payload, send_json_fn):
    from github import (
        prepare_issue_worktree, spawn_pty, resolve_agent, build_agent_cmd,
        agent_short, USER_SHELL, REPO_ROOT,
    )
    import shlex
    try:
        agent_id = payload.get("agent", "")
        issue_numbers = payload.get("issueNumbers", [])
        cols = int(payload.get("cols") or 3)
        rows = int(payload.get("rows") or 2)
    except (TypeError, ValueError):
        return send_json_fn(handler, {"error": "invalid payload"}, 400)

    if not isinstance(issue_numbers, list) or len(issue_numbers) == 0:
        return send_json_fn(handler, {"error": "issueNumbers must be a non-empty list"}, 400)

    agent = resolve_agent(agent_id)
    total_cells = cols * rows
    issue_nums = issue_numbers[:total_cells]
    if len(issue_nums) < total_cells:
        return send_json_fn(handler, {"error": f"need {total_cells} issues, got {len(issue_nums)}"}, 400)

    # Build cell labels: A1, B1, C1, A2, B2, C2 for 3x2
    cell_labels = []
    for r in range(rows):
        for c in range(cols):
            cell_labels.append(chr(65 + r) + str(c + 1))

    created = []
    errors = []
    for idx, issue_num in enumerate(issue_nums):
        cell = cell_labels[idx]
        label = f"grid-{cell} · #{issue_num}"
        prep = prepare_issue_worktree(issue_num)
        if prep.get("error"):
            errors.append({"cell": cell, "issue": issue_num, "error": prep["error"]})
            continue
        wt = prep.get("worktree", "")
        prompt_file = prep.get("prompt_file") or ""

        agent_cmd = build_agent_cmd(agent, '$(cat "$AGENT_PROMPT_FILE")')
        env_extra = {
            "AGENT_ISSUE": str(issue_num),
            "AGENT_BRANCH": prep.get("branch", ""),
            "AGENT_PROMPT_FILE": prompt_file,
            "PS1": f"\\[\\e[33m\\]grid-{cell} · #{issue_num}\\[\\e[0m\\]:\\W$ ",
        }
        wrapper = (
            'echo "──── starting {bin} ({yolo_short}) grid cell {cell} on issue #{issue} ────"; '
            'echo "      agent:  {agent_label}"; '
            'echo "      model:  {model}"; '
            'echo "      cell:   {cell}"; '
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
            cell=cell,
            issue=issue_num,
            agent_label=agent["label"],
            model=agent.get("model") or "(agent default)",
            agent_cmd=agent_cmd,
            shell=shlex.quote(USER_SHELL),
        )
        argv = ["bash", "-c", wrapper]
        sess = spawn_pty(
            argv,
            cwd=str(REPO_ROOT / wt) if wt else str(REPO_ROOT),
            env_extra=env_extra,
            label=label,
            rows=30,
            cols=120,
            meta={
                "kind": "agent-grid-cell",
                "cell": cell,
                "issue": issue_num,
                "branch": prep.get("branch", ""),
                "worktree": wt,
                "prompt_file": prompt_file,
            },
        )
        created.append({"cell": cell, "sid": sess["sid"], "issue": issue_num})

    _AGENT_GRID["active"] = True
    _AGENT_GRID["agent"] = agent_id
    _AGENT_GRID["sessions"] = created

    return send_json_fn(handler, {
        "launched": True,
        "cells": created,
        "errors": errors,
        "total": total_cells,
    })


def _handle_agent_grid_close(handler, payload, send_json_fn):
    from github import list_ptys, kill_pty, delete_pty
    grid_sids = [s["sid"] for s in list_ptys() if s.get("kind") == "agent-grid-cell"]
    for sid in grid_sids:
        kill_pty(sid)
        delete_pty(sid)
    _AGENT_GRID["active"] = False
    _AGENT_GRID["sessions"] = []
    return send_json_fn(handler, {"closed": True, "killed": len(grid_sids)})
