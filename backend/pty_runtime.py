"""PTY session runtime — tmux-backed so sessions survive daemon restarts.

Each logical session maps to a tmux session named ``gs-<sid>`` running on a
dedicated tmux socket (``-L gitswarm``). The tmux server owns the actual PTY,
so the gitswarm daemon — and the web server — can be killed and restarted
without losing any running command. On daemon startup we discover existing
``gs-*`` tmux sessions and re-attach to them.

Per-session state on disk:
    <REPO_ROOT>/.gitswarm/sessions/<sid>/
        meta.json   — label, cwd, argv, started, kind/issue/pr
        out.log     — raw bytes captured via ``tmux pipe-pane``
        start.sh    — wrapper that exports env, cds, and execs the command
"""
import json
import os
import re
import secrets
import shlex
import shutil
import subprocess
import threading
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
USER_SHELL = os.environ.get("SHELL", "/bin/bash")


def _resolve_tmux():
    override = os.environ.get("GITSWARM_TMUX_BIN")
    if override and Path(override).is_file() and os.access(override, os.X_OK):
        return override
    for candidate in ("/opt/homebrew/bin/tmux", "/usr/local/bin/tmux", "/usr/bin/tmux"):
        if Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    return shutil.which("tmux") or "tmux"


TMUX_BIN = _resolve_tmux()
TMUX_SOCKET = "gitswarm"
SESS_PREFIX = "gs-"
SESS_DIR = REPO_ROOT / ".gitswarm" / "sessions"

_PTY_SESSIONS = {}
_PTY_LOCK = threading.Lock()
_PTY_BUF_CAP = 4 * 1024 * 1024
_INIT_LOCK = threading.Lock()
_DISCOVERED = False


def _tmux(*args, timeout=10):
    """Run a tmux command on our dedicated socket. Returns CompletedProcess."""
    cmd = [TMUX_BIN, "-L", TMUX_SOCKET, *args]
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as e:
        raise RuntimeError(
            "tmux not found in PATH (install with: brew install tmux)"
        ) from e


def _tmux_has_session(target):
    return _tmux("has-session", "-t", target).returncode == 0


def _pane_dead(target):
    res = _tmux("display-message", "-t", target, "-p", "#{pane_dead}")
    return res.returncode == 0 and res.stdout.strip() == "1"


def init(repo_root: Path = None, user_shell: str = None):
    """Set REPO_ROOT/USER_SHELL and adopt any pre-existing tmux sessions."""
    global REPO_ROOT, USER_SHELL, SESS_DIR, _DISCOVERED
    with _INIT_LOCK:
        if repo_root is not None:
            REPO_ROOT = Path(repo_root)
            SESS_DIR = REPO_ROOT / ".gitswarm" / "sessions"
        if user_shell is not None:
            USER_SHELL = user_shell
        SESS_DIR.mkdir(parents=True, exist_ok=True)
        _discover_existing()
        _DISCOVERED = True


def _discover_existing():
    """Find ``gs-*`` tmux sessions left over from a prior daemon and adopt them."""
    try:
        res = _tmux(
            "list-sessions",
            "-F",
            "#{session_name}|#{window_width}|#{window_height}",
        )
    except RuntimeError:
        return
    if res.returncode != 0:
        return
    for line in res.stdout.strip().splitlines():
        try:
            name, cols_s, rows_s = line.split("|")
        except ValueError:
            continue
        if not name.startswith(SESS_PREFIX):
            continue
        sid = name[len(SESS_PREFIX):]
        if sid in _PTY_SESSIONS:
            continue
        meta = {}
        meta_path = SESS_DIR / sid / "meta.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
            except (OSError, json.JSONDecodeError):
                meta = {}
        try:
            cols, rows = int(cols_s), int(rows_s)
        except ValueError:
            cols, rows = 120, 30
        _adopt(sid, meta, cols, rows)


def _adopt(sid, meta, cols, rows):
    """Build an in-memory record for a tmux session that already exists."""
    with _PTY_LOCK:
        if sid in _PTY_SESSIONS:
            return _PTY_SESSIONS[sid]
    sess_dir = SESS_DIR / sid
    sess_dir.mkdir(parents=True, exist_ok=True)
    out_log = sess_dir / "out.log"
    out_log.touch(exist_ok=True)

    sess = {
        "sid": sid,
        "label": meta.get("label") or f"{SESS_PREFIX}{sid}",
        "cwd": meta.get("cwd", ""),
        "argv": list(meta.get("argv") or []),
        "started": meta.get("started", time.time()),
        "last_output": time.time(),
        "last_input": time.time(),
        "rows": rows,
        "cols": cols,
        "buf": bytearray(),
        "drop": 0,
        "cond": threading.Condition(),
        "alive": True,
        "exit_status": None,
        "meta": dict(meta.get("meta_extra") or {}),
        "out_log": str(out_log),
        "tail_pos": 0,
        "fd": None,
        "pid": None,
    }
    try:
        size = out_log.stat().st_size
        with open(out_log, "rb") as f:
            if size > _PTY_BUF_CAP:
                f.seek(size - _PTY_BUF_CAP)
                sess["drop"] = size - _PTY_BUF_CAP
            sess["buf"].extend(f.read())
        sess["tail_pos"] = size
    except OSError:
        pass

    with _PTY_LOCK:
        _PTY_SESSIONS[sid] = sess

    _ensure_pipe(sid)
    threading.Thread(target=_pty_tailer, args=(sid,), daemon=True).start()
    return sess


def _ensure_pipe(sid):
    """Make sure pipe-pane is writing this session's output to its out.log."""
    sess = _PTY_SESSIONS.get(sid)
    if not sess:
        return
    target = f"{SESS_PREFIX}{sid}"
    res = _tmux("display-message", "-t", target, "-p", "#{pane_pipe}")
    if res.returncode == 0 and res.stdout.strip() == "1":
        return
    cmd = f"cat >> {shlex.quote(sess['out_log'])}"
    _tmux("pipe-pane", "-t", target, cmd)


def _clean_child_env():
    env = os.environ.copy()
    drop = [
        "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST",
        "CLAUDE_CODE_SDK_HAS_OAUTH_REFRESH",
        "CLAUDE_CODE_ENTRYPOINT",
        "CLAUDE_AGENT_SDK_VERSION",
        "CLAUDE_CODE_EMIT_TOOL_USE_SUMMARIES",
        "CLAUDE_CODE_ENABLE_ASK_USER_QUESTION_TOOL",
        "CLAUDE_CODE_DISABLE_CRON",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC",
        "CLAUDE_CODE_SESSION_ID",
        "CLAUDE_CODE_REMOTE_SESSION_ID",
        "CLAUDE_CODE_RESUME_INTERRUPTED_TURN",
        "CLAUDE_CODE_RESUME_PROMPT",
        "SESSION_ID",
        "REMOTE_SESSION_ID",
        "RESUME_INTERRUPTED_TURN",
        "RESUME_PROMPT",
        "MINIMAX_SESSION_ID",
        "MINIMAX_REMOTE_SESSION_ID",
        "MINIMAX_RESUME_INTERRUPTED_TURN",
        "MINIMAX_RESUME_PROMPT",
        "CMF_SESSION_ID",
        "CMF_REMOTE_SESSION_ID",
        "CMF_RESUME_INTERRUPTED_TURN",
        "CMF_RESUME_PROMPT",
    ]
    for k in drop:
        env.pop(k, None)
    if "ANTHROPIC_API_KEY" in env and not env["ANTHROPIC_API_KEY"].strip():
        env.pop("ANTHROPIC_API_KEY")
    for k in (
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_MODEL",
        "ANTHROPIC_DEFAULT_SONNET_MODEL",
        "ANTHROPIC_DEFAULT_OPUS_MODEL",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL",
        "API_TIMEOUT_MS",
    ):
        env.pop(k, None)
    return env


def spawn_pty(argv, cwd=None, env_extra=None, label="", rows=30, cols=120, meta=None):
    """Create a tmux session that owns the PTY for ``argv``."""
    if not _DISCOVERED:
        init()
    if isinstance(argv, str):
        argv = shlex.split(argv)
    argv = list(argv)

    sid = secrets.token_hex(6)
    target = f"{SESS_PREFIX}{sid}"
    sess_dir = SESS_DIR / sid
    sess_dir.mkdir(parents=True, exist_ok=True)

    env = _clean_child_env()
    env["TERM"] = "xterm-256color"
    env["COLORTERM"] = "truecolor"
    if env_extra:
        env.update(env_extra)

    cwd_resolved = cwd or os.getcwd()
    start_sh = sess_dir / "start.sh"
    lines = ["#!/bin/bash"]
    for k, v in env.items():
        sv = str(v)
        if "\n" in sv or "\r" in sv or "\x00" in sv:
            continue
        lines.append(f"export {k}={shlex.quote(sv)}")
    lines.append(f"cd {shlex.quote(str(cwd_resolved))} 2>/dev/null || true")
    lines.append(f"exec {shlex.join(argv)}")
    start_sh.write_text("\n".join(lines) + "\n")
    os.chmod(start_sh, 0o755)

    meta_dict = {
        "label": label or " ".join(argv),
        "cwd": str(cwd_resolved),
        "argv": argv,
        "started": time.time(),
        "rows": rows,
        "cols": cols,
        "meta_extra": dict(meta or {}),
    }
    (sess_dir / "meta.json").write_text(json.dumps(meta_dict))

    res = _tmux(
        "new-session", "-d",
        "-s", target,
        "-x", str(cols),
        "-y", str(rows),
        str(start_sh),
    )
    if res.returncode != 0:
        raise RuntimeError(
            f"tmux new-session failed: {res.stderr.strip() or res.stdout.strip()}"
        )
    # Keep the pane around after the process exits so we can show its tail.
    _tmux("set-option", "-t", target, "remain-on-exit", "on")

    return _adopt(sid, meta_dict, cols, rows)


_WAIT_RE = re.compile(
    r"[>?]$|:$|\btype\b|\bready\b|\bwaiting\b|\bpress\b|\binput\b",
    re.IGNORECASE,
)


def _update_waiting(sess, chunk):
    try:
        text = chunk.decode("utf-8", errors="replace")
    except Exception:
        return
    lines = text.split("\n")
    if lines:
        last = lines[-1].rstrip()
        sess["waiting_for_input"] = bool(last and _WAIT_RE.search(last))


def _pty_tailer(sid):
    sess = _PTY_SESSIONS.get(sid)
    if not sess:
        return
    out_log = Path(sess["out_log"])
    target = f"{SESS_PREFIX}{sid}"
    try:
        f = open(out_log, "rb")
        f.seek(sess["tail_pos"])
    except OSError:
        sess["alive"] = False
        return

    idle_polls = 0
    try:
        while True:
            chunk = f.read(65536)
            if chunk:
                idle_polls = 0
                with sess["cond"]:
                    sess["last_output"] = time.time()
                    sess["buf"].extend(chunk)
                    excess = len(sess["buf"]) - _PTY_BUF_CAP
                    if excess > 0:
                        del sess["buf"][:excess]
                        sess["drop"] += excess
                    sess["cond"].notify_all()
                sess["tail_pos"] = f.tell()
                _update_waiting(sess, chunk)
                continue

            idle_polls += 1
            if idle_polls % 4 == 0:
                if not _tmux_has_session(target):
                    break
                if _pane_dead(target):
                    time.sleep(0.05)
                    tail = f.read(65536)
                    if tail:
                        with sess["cond"]:
                            sess["buf"].extend(tail)
                            sess["last_output"] = time.time()
                            sess["cond"].notify_all()
                        sess["tail_pos"] = f.tell()
                    break
            time.sleep(0.05)
    finally:
        try:
            f.close()
        except OSError:
            pass
        sess["alive"] = False
        with sess["cond"]:
            sess["cond"].notify_all()


def pty_write(sid, data) -> bool:
    sess = _PTY_SESSIONS.get(sid)
    if not sess or not sess.get("alive"):
        return False
    if not isinstance(data, (bytes, bytearray, memoryview)):
        data = str(data).encode("utf-8")
    data = bytes(data)
    if not data:
        return True
    target = f"{SESS_PREFIX}{sid}"
    hex_str = data.hex()
    pairs = [hex_str[i:i + 2] for i in range(0, len(hex_str), 2)]
    CHUNK = 512
    for i in range(0, len(pairs), CHUNK):
        res = _tmux("send-keys", "-t", target, "-H", *pairs[i:i + CHUNK])
        if res.returncode != 0:
            return False
    sess["last_input"] = time.time()
    return True


def pty_resize(sid, rows, cols):
    sess = _PTY_SESSIONS.get(sid)
    if not sess:
        return False
    target = f"{SESS_PREFIX}{sid}"
    res = _tmux("resize-window", "-t", target, "-x", str(cols), "-y", str(rows))
    if res.returncode != 0:
        return False
    sess["rows"], sess["cols"] = rows, cols
    return True


def pty_rename(sid, label):
    sess = _PTY_SESSIONS.get(sid)
    if not sess:
        return False
    sess["label"] = label
    meta_path = SESS_DIR / sid / "meta.json"
    try:
        meta = json.loads(meta_path.read_text())
        meta["label"] = label
        meta_path.write_text(json.dumps(meta))
    except (OSError, json.JSONDecodeError):
        pass
    return True


def pty_read(sid, offset, timeout=20):
    sess = _PTY_SESSIONS.get(sid)
    if not sess:
        return None
    deadline = time.time() + timeout
    with sess["cond"]:
        while True:
            drop = sess["drop"]
            logical_len = drop + len(sess["buf"])
            if offset > logical_len:
                return bytes(sess["buf"]), logical_len, sess["alive"], drop, True
            if offset < drop:
                return bytes(sess["buf"]), logical_len, sess["alive"], drop, True
            buf_off = offset - drop
            if buf_off < len(sess["buf"]):
                return bytes(sess["buf"][buf_off:]), logical_len, sess["alive"], drop, False
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
    target = f"{SESS_PREFIX}{sid}"
    _tmux("kill-session", "-t", target)
    sess["alive"] = False
    with sess["cond"]:
        sess["cond"].notify_all()
    return True


def delete_pty(sid):
    sess = _PTY_SESSIONS.get(sid)
    if not sess:
        return False
    kill_pty(sid)
    with _PTY_LOCK:
        _PTY_SESSIONS.pop(sid, None)
    shutil.rmtree(SESS_DIR / sid, ignore_errors=True)
    return True


def list_ptys():
    with _PTY_LOCK:
        return [
            {
                "sid": s["sid"],
                "label": s["label"],
                "cwd": s["cwd"],
                "alive": s["alive"],
                "issue": s.get("meta", {}).get("issue"),
                "kind": s.get("meta", {}).get("kind"),
                "pr": s.get("meta", {}).get("pr"),
                "started": s["started"],
                "last_output": s.get("last_output") or s["started"],
                "last_input": s.get("last_input") or s["started"],
                "rows": s["rows"],
                "cols": s["cols"],
            }
            for s in _PTY_SESSIONS.values()
        ]


def live_issue_pty(issue_num: int):
    issue_num = int(issue_num)
    with _PTY_LOCK:
        for s in _PTY_SESSIONS.values():
            if not s.get("alive"):
                continue
            meta = s.get("meta") or {}
            if str(meta.get("issue")) == str(issue_num):
                return s
            label = s.get("label") or ""
            if re.search(rf"#{re.escape(str(issue_num))}\b", label):
                return s
    return None


def reap_dead_ptys(max_age_dead=600):
    now = time.time()
    with _PTY_LOCK:
        dead = [
            sid for sid, s in _PTY_SESSIONS.items()
            if not s["alive"] and (now - s["started"]) > max_age_dead
        ]
        for sid in dead:
            _PTY_SESSIONS.pop(sid, None)
            shutil.rmtree(SESS_DIR / sid, ignore_errors=True)


def pty_in_use(worktree_path: Path) -> bool:
    prefix = str(worktree_path)
    with _PTY_LOCK:
        for sess in _PTY_SESSIONS.values():
            cwd = sess.get("cwd") or ""
            if cwd == prefix or cwd.startswith(prefix + os.sep):
                return True
    return False


def _safe_relpath(p: Path) -> str:
    try:
        return str(p.relative_to(REPO_ROOT))
    except ValueError:
        return str(p)


def spawn_shell_session(cwd: Path, label: str = "", env_extra=None):
    if not cwd.exists():
        return {"error": f"cwd does not exist: {cwd}"}
    argv = [USER_SHELL, "-i"]
    sess = spawn_pty(
        argv,
        cwd=str(cwd),
        env_extra=env_extra,
        label=label or f"shell · {_safe_relpath(cwd)}",
        meta={"kind": "shell"},
    )
    return {"sid": sess["sid"], "label": sess["label"], "cwd": sess["cwd"]}
