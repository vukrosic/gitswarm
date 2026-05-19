"""PTY daemon client — talks to the detached PTY daemon over a Unix socket."""
import json
import os
import re
import shlex
import socket
import subprocess
import sys
import time
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parent.parent
SOCK_PATH = APP_ROOT / ".gitswarm/pty_daemon.sock"
_DAEMON_PID_FILE = APP_ROOT / ".gitswarm/pty_daemon.pid"
REPO_ROOT = Path.cwd().resolve()
USER_SHELL = os.environ.get("SHELL", "/bin/bash")


def init(repo_root: Path, user_shell: str):
    global REPO_ROOT, USER_SHELL
    REPO_ROOT = Path(repo_root).expanduser().resolve()
    USER_SHELL = user_shell


def _daemon_script() -> Path:
    return APP_ROOT / "backend" / "pty_daemon.py"


def daemon_pid() -> int | None:
    """Return the daemon PID if it's running, else None."""
    try:
        pid_str = _DAEMON_PID_FILE.read_text().strip()
        pid = int(pid_str)
        os.kill(pid, 0)
        return pid
    except (FileNotFoundError, ValueError, ProcessLookupError, PermissionError):
        return None


def is_daemon_running() -> bool:
    return daemon_pid() is not None


def _request(req, timeout=30, retries=1):
    last_exc = None
    for attempt in range(retries + 1):
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                sock.connect(str(SOCK_PATH))
                with sock.makefile("rwb") as fp:
                    fp.write((json.dumps(req) + "\n").encode())
                    fp.flush()
                    line = fp.readline()
                    if not line:
                        raise ConnectionError("daemon closed the connection")
                    return json.loads(line.decode())
        except (OSError, json.JSONDecodeError, ConnectionError) as exc:
            last_exc = exc
            if attempt >= retries:
                raise
            ensure_daemon()
            time.sleep(0.1)
    if last_exc:
        raise last_exc


def _daemon_ready(timeout=0.2) -> bool:
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect(str(SOCK_PATH))
            with sock.makefile("rwb") as fp:
                fp.write(b'{"cmd":"ping"}\n')
                fp.flush()
                line = fp.readline()
                if not line:
                    return False
                resp = json.loads(line.decode())
                return bool(resp.get("ok"))
    except (OSError, json.JSONDecodeError, ConnectionError):
        return False


def ensure_daemon() -> bool:
    """Start the PTY daemon if needed and wait until the socket is ready."""
    if _daemon_ready():
        return True

    pid = daemon_pid()
    if pid is not None:
        for _ in range(20):
            if _daemon_ready():
                return True
            time.sleep(0.1)
        return False

    if SOCK_PATH.exists():
        SOCK_PATH.unlink(missing_ok=True)
    if _DAEMON_PID_FILE.exists():
        _DAEMON_PID_FILE.unlink(missing_ok=True)

    subprocess.Popen(
        [sys.executable, str(_daemon_script())],
        cwd=str(APP_ROOT),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        start_new_session=True,
    )

    for _ in range(50):
        if _daemon_ready():
            return True
        time.sleep(0.1)
    return False


def shutdown_daemon():
    """Tell the daemon to shutdown and wait for it to exit."""
    try:
        _request({"cmd": "shutdown"}, timeout=5, retries=0)
    except Exception:
        pass
    for _ in range(20):
        if not is_daemon_running():
            break
        time.sleep(0.25)


def ping():
    return _request({"cmd": "ping"})["data"]


def list_ptys():
    """Return a list of session dicts."""
    return _request({"cmd": "list"})["data"]["sessions"]


def list_ptys_for_repo(repo_root=None):
    root = Path(repo_root).expanduser().resolve() if repo_root else REPO_ROOT
    out = []
    for sess in list_ptys():
        cwd = Path(sess.get("cwd") or "")
        meta = sess.get("meta") or {}
        meta_root = meta.get("repo_root") or meta.get("project_root") or ""
        if meta_root:
            try:
                if Path(meta_root).expanduser().resolve() == root:
                    out.append(sess)
                    continue
            except Exception:
                pass
        try:
            cwd.relative_to(root)
            out.append(sess)
        except Exception:
            continue
    return out


def reap_dead_ptys():
    """Force the daemon to compact dead PTYs by asking for a fresh snapshot."""
    list_ptys()


def pty_read(sid, offset=0, timeout=20):
    """Return (data_bytes, logical_len, alive, drop, reset) tuple."""
    result = _request({"cmd": "read", "sid": sid, "offset": offset, "timeout": timeout})
    if not result.get("ok"):
        return None
    d = result["data"]
    data = d["data"].encode("latin-1") if isinstance(d["data"], str) else bytes(d["data"])
    return data, d["logical_len"], d["alive"], d["drop"], d["reset"]


def pty_write(sid, data):
    return _request({"cmd": "write", "sid": sid, "data": data}).get("ok", False)


def pty_resize(sid, rows, cols):
    return _request({"cmd": "resize", "sid": sid, "rows": rows, "cols": cols}).get("ok", False)


def pty_rename(sid, label):
    return _request({"cmd": "rename", "sid": sid, "label": label}).get("ok", False)


def kill_pty(sid):
    return _request({"cmd": "kill", "sid": sid}).get("ok", False)


def delete_pty(sid):
    return _request({"cmd": "delete", "sid": sid}).get("ok", False)


def spawn_pty(argv, cwd=None, env_extra=None, label="", rows=30, cols=120, meta=None):
    if isinstance(argv, str):
        argv = shlex.split(argv)
    meta_out = dict(meta or {})
    meta_out.setdefault("repo_root", str(REPO_ROOT))
    meta_out.setdefault("project_root", str(REPO_ROOT))
    return _request({
        "cmd": "spawn",
        "argv": argv,
        "cwd": cwd,
        "env_extra": env_extra,
        "label": label,
        "rows": rows,
        "cols": cols,
        "meta": meta_out or None,
    })["data"]


def spawn_shell_session(cwd, label="", env_extra=None):
    cwd = Path(cwd)
    if not cwd.exists():
        return {"error": f"cwd does not exist: {cwd}"}
    try:
        rel = cwd.relative_to(REPO_ROOT)
        rel_label = str(rel)
    except ValueError:
        rel_label = str(cwd)
    sess = spawn_pty(
        [USER_SHELL, "-i"],
        cwd=str(cwd),
        env_extra=env_extra,
        label=label or f"shell · {rel_label}",
        meta={"kind": "shell", "repo_root": str(REPO_ROOT)},
    )
    return {"sid": sess["sid"], "label": sess["label"], "cwd": sess["cwd"]}


def live_issue_pty(issue_num: int):
    issue_num = int(issue_num)
    for s in list_ptys_for_repo(REPO_ROOT):
        if not s.get("alive"):
            continue
        meta = s.get("meta") or {}
        if str(meta.get("issue")) == str(issue_num):
            return s
        label = s.get("label") or ""
        if re.search(rf"#{re.escape(str(issue_num))}\b", label):
            return s
    return None


def pty_in_use(worktree_path: Path) -> bool:
    prefix = str(worktree_path)
    for sess in list_ptys_for_repo(REPO_ROOT):
        cwd = sess.get("cwd") or ""
        if cwd == prefix or cwd.startswith(prefix + os.sep):
            return True
    return False
