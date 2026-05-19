"""PTY daemon — a detached Unix-socket server that owns all PTY sessions.

The dashboard can restart independently and reconnect to the existing daemon.
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

import pty_runtime

REPO_ROOT = Path(__file__).resolve().parent.parent
SOCK_PATH = REPO_ROOT / ".gitswarm/pty_daemon.sock"
_PID_FILE = REPO_ROOT / ".gitswarm/pty_daemon.pid"
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
            sess = await asyncio.to_thread(
                pty_runtime.spawn_pty,
                argv if isinstance(argv, list) else shlex.split(argv),
                cwd=cwd,
                env_extra=env_extra,
                label=label,
                rows=rows,
                cols=cols,
                meta=meta,
            )
            out = {"ok": True, "data": {
                "sid": sess["sid"], "label": sess["label"], "cwd": sess["cwd"],
            }}

        elif cmd == "read":
            offset = int(req.get("offset", 0))
            timeout = float(req.get("timeout", 20))
            # Long-poll reads can wait for output. Keep them off the asyncio
            # event loop so input/write requests are not stuck behind a stream.
            res = await asyncio.to_thread(pty_runtime.pty_read, sid, offset, timeout=timeout)
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
            ok = await asyncio.to_thread(pty_runtime.pty_write, sid, data_str.encode("utf-8"))
            out = {"ok": ok}

        elif cmd == "resize":
            rows = int(req.get("rows", 30))
            cols = int(req.get("cols", 120))
            ok = await asyncio.to_thread(pty_runtime.pty_resize, sid, rows, cols)
            out = {"ok": ok}

        elif cmd == "rename":
            label = req.get("label", "")
            ok = await asyncio.to_thread(pty_runtime.pty_rename, sid, label)
            out = {"ok": ok}

        elif cmd == "kill":
            ok = await asyncio.to_thread(pty_runtime.kill_pty, sid)
            out = {"ok": ok}

        elif cmd == "delete":
            ok = await asyncio.to_thread(pty_runtime.delete_pty, sid)
            out = {"ok": ok}

        elif cmd == "list":
            await asyncio.to_thread(pty_runtime.reap_dead_ptys)
            sessions = await asyncio.to_thread(pty_runtime.list_ptys)
            out = {"ok": True, "data": {"sessions": sessions}}

        elif cmd == "shutdown":
            global SHUTDOWN
            SHUTDOWN = True
            # Sessions live in tmux and survive — do NOT kill them on daemon shutdown.
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

    # Adopt any tmux-backed sessions that survived a previous daemon.
    pty_runtime.init(REPO_ROOT, os.environ.get("SHELL", "/bin/bash"))

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
