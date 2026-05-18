"""PTY session runtime for the dashboard."""
import fcntl
import os
import pty
import re
import secrets
import select
import shlex
import signal
import struct
import termios
import threading
import time
from pathlib import Path


REPO_ROOT = None
USER_SHELL = os.environ.get("SHELL", "/bin/bash")

_PTY_SESSIONS = {}
_PTY_LOCK = threading.Lock()
_PTY_BUF_CAP = 4 * 1024 * 1024


def _close_session_fd(sess):
    fd = sess.get("fd")
    if fd is None:
        return
    sess["fd"] = None
    try:
        os.close(fd)
    except OSError:
        pass


def init(repo_root: Path, user_shell: str):
    global REPO_ROOT, USER_SHELL
    REPO_ROOT = repo_root
    USER_SHELL = user_shell


def _set_winsize(fd, rows, cols):
    try:
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
    except OSError:
        pass


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
    """Fork a child under a PTY and keep an in-memory output ring buffer."""
    if isinstance(argv, str):
        argv = shlex.split(argv)
    sid = secrets.token_hex(6)
    pid, fd = pty.fork()
    if pid == 0:
        try:
            if cwd:
                os.chdir(cwd)
            env = _clean_child_env()
            env["TERM"] = "xterm-256color"
            env["COLORTERM"] = "truecolor"
            if env_extra:
                env.update(env_extra)
            os.environ.clear()
            for k, v in env.items():
                os.environ[k] = str(v)
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
        "rows": rows,
        "cols": cols,
        "buf": bytearray(),
        "drop": 0,
        "cond": threading.Condition(),
        "alive": True,
        "exit_status": None,
        "meta": dict(meta or {}),
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
    if fd is None:
        return
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
                    excess = len(sess["buf"]) - _PTY_BUF_CAP
                    if excess > 0:
                        del sess["buf"][:excess]
                        sess["drop"] += excess
                    sess["cond"].notify_all()
                    text = chunk.decode("utf-8", errors="replace")
                    lines = text.split("\n")
                    if lines:
                        last = lines[-1].rstrip()
                        sess["waiting_for_input"] = bool(
                            last and re.search(
                                r"[>?]$|:$|\btype\b|\bready\b|\bwaiting\b|\bpress\b|\binput\b",
                                last,
                                re.IGNORECASE,
                            )
                        )
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
    _close_session_fd(sess)
    with sess["cond"]:
        sess["cond"].notify_all()


def pty_write(sid, data: bytes) -> bool:
    sess = _PTY_SESSIONS.get(sid)
    if not sess or not sess["alive"] or sess.get("fd") is None:
        return False
    try:
        os.write(sess["fd"], data)
        sess["last_input"] = time.time()
        return True
    except OSError:
        return False


def pty_resize(sid, rows, cols):
    sess = _PTY_SESSIONS.get(sid)
    if not sess or sess.get("fd") is None:
        return False
    _set_winsize(sess["fd"], rows, cols)
    sess["rows"], sess["cols"] = rows, cols
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
    try:
        os.killpg(os.getpgid(sess["pid"]), signal.SIGHUP)
    except Exception:
        try:
            os.kill(sess["pid"], signal.SIGHUP)
        except OSError:
            pass
    sess["alive"] = False
    return True


def delete_pty(sid):
    sess = _PTY_SESSIONS.get(sid)
    if not sess:
        return False
    kill_pty(sid)
    with _PTY_LOCK:
        sess = _PTY_SESSIONS.pop(sid, None)
    if not sess:
        return False
    _close_session_fd(sess)
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
            sid
            for sid, s in _PTY_SESSIONS.items()
            if not s["alive"] and (now - s["started"]) > max_age_dead
        ]
        for sid in dead:
            _PTY_SESSIONS.pop(sid, None)


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
