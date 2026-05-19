"""PTY daemon — a standalone Unix-socket server that owns all PTY sessions.

Survives server.py restarts (SIGHUP graceful reload). The daemon runs as a
child of the server process; when the server dies uncleanly the daemon is
reaped automatically.

Protocol: JSON messages over a Unix domain socket.
  Request:  {"cmd": "...", "sid"?: "...", ...}
  Response: {"ok": true, "data": ...}  or  {"ok": false, "error": "..."}
"""
import asyncio
import json
import os
import shlex
import signal
import sys
from pathlib import Path

# Add parent to path so we can import pty_runtime
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pty_runtime

SOCK_PATH = Path(".gitswarm/pty_daemon.sock")
_PID_FILE = Path(".gitswarm/pty_daemon.pid")
SHUTDOWN = False


def _json(data):
    return json.dumps(data).encode()


async def handle_client(reader, writer):
    """Handle one client connection — read JSON request, dispatch, reply."""
    try:
        data = await reader.readuntil(b"\n")
        req = json.loads(data.decode())
    except (json.JSONDecodeError, ConnectionResetError, asyncio.exceptions.IncompleteReadError):
        writer.write(_json({"ok": False, "error": "bad request"}))
        await writer.drain()
        writer.close()
        return

    cmd = req.get("cmd", "")
    sid = req.get("sid", "")

    try:
        if cmd == "ping":
            out = {"ok": True, "data": "pong"}

        elif cmd == "spawn":
            argv = req.get("argv")
            cwd = req.get("cwd")
            env_extra = req.get("env_extra")
            label = req.get("label", "")
            rows = int(req.get("rows", 30))
            cols = int(req.get("cols", 120))
            meta = req.get("meta")
            sess = pty_runtime.spawn_pty(
                argv if isinstance(argv, list) else shlex.split(argv),
                cwd=cwd, env_extra=env_extra, label=label,
                rows=rows, cols=cols, meta=meta,
            )
            out = {"ok": True, "data": {
                "sid": sess["sid"], "label": sess["label"], "cwd": sess["cwd"],
            }}

        elif cmd == "read":
            offset = int(req.get("offset", 0))
            timeout = float(req.get("timeout", 20))
            res = pty_runtime.pty_read(sid, offset, timeout=timeout)
            if res is None:
                out = {"ok": False, "error": "unknown sid"}
            else:
                data, logical_len, alive, drop, reset = res
                out = {"ok": True, "data": {
                    "data": data.decode("latin-1"),  # octet stream — send as string
                    "logical_len": logical_len,
                    "alive": alive,
                    "drop": drop,
                    "reset": reset,
                }}

        elif cmd == "write":
            data_str = req.get("data", "")
            ok = pty_runtime.pty_write(sid, data_str.encode("utf-8"))
            out = {"ok": ok}

        elif cmd == "resize":
            rows = int(req.get("rows", 30))
            cols = int(req.get("cols", 120))
            ok = pty_runtime.pty_resize(sid, rows, cols)
            out = {"ok": ok}

        elif cmd == "rename":
            label = req.get("label", "")
            ok = pty_runtime.pty_rename(sid, label)
            out = {"ok": ok}

        elif cmd == "kill":
            ok = pty_runtime.kill_pty(sid)
            out = {"ok": ok}

        elif cmd == "delete":
            ok = pty_runtime.delete_pty(sid)
            out = {"ok": ok}

        elif cmd == "list":
            pty_runtime.reap_dead_ptys()
            sessions = pty_runtime.list_ptys()
            out = {"ok": True, "data": {"sessions": sessions}}

        elif cmd == "shutdown":
            global SHUTDOWN
            SHUTDOWN = True
            # Kill all PTYs then exit
            for sess in pty_runtime.list_ptys():
                pty_runtime.kill_pty(sess["sid"])
                pty_runtime.delete_pty(sess["sid"])
            out = {"ok": True, "data": "daemon shutting down"}

        else:
            out = {"ok": False, "error": f"unknown command: {cmd}"}

    except Exception as e:
        out = {"ok": False, "error": str(e)}

    writer.write(_json(out))
    await writer.drain()
    writer.close()


async def main():
    """Run the async Unix socket server."""
    global SHUTDOWN

    # Clean up stale socket
    if SOCK_PATH.exists():
        SOCK_PATH.unlink()
    SOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    _PID_FILE.write_text(str(os.getpid()))

    # Signal handlers for graceful shutdown
    def handle_sigterm():
        global SHUTDOWN
        SHUTDOWN = True

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handle_sigterm)

    srv = await asyncio.start_unix_server(handle_client, str(SOCK_PATH))
    print(f"pty_daemon: listening on {SOCK_PATH}", flush=True)

    # Wait for shutdown signal
    while not SHUTDOWN:
        await asyncio.sleep(1)

    srv.close()
    await srv.wait_closed()
    if SOCK_PATH.exists():
        SOCK_PATH.unlink()
    if _PID_FILE.exists():
        _PID_FILE.unlink()
    print("pty_daemon: exited", flush=True)


if __name__ == "__main__":
    asyncio.run(main())