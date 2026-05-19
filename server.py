#!/usr/bin/env python3
"""gitswarm dashboard server."""
import asyncio
from pathlib import Path

_HERE = Path(__file__).resolve().parent

import http.server
import json
import os
import signal
import sys
from urllib.parse import parse_qs, urlparse

from backend.static import init as static_init, maybe_serve_frontend
from backend.reload import init as reload_init
from backend.http import send_json
from github import STATE_DIR, WORKTREES_DIR


WEB_DIR = _HERE / "web"
WEB_DIST_DIR = WEB_DIR / "dist"
WEB_INDEX_HTML = WEB_DIST_DIR / "index.html"

static_init(WEB_DIR, WEB_DIST_DIR, WEB_INDEX_HTML)
reload_init(_HERE, WEB_DIR, WEB_DIST_DIR)


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        u = urlparse(self.path)
        qs = parse_qs(u.query)

        if maybe_serve_frontend(self, u.path):
            return

        from backend.routes import dispatch_get
        dispatch_get(self, u, qs, send_json)

    def do_POST(self):
        u = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length).decode() if content_length else ""
        try:
            payload = json.loads(body or "{}")
        except json.JSONDecodeError:
            return send_json(self, {"error": "bad json"}, 400)

        from backend.routes import dispatch_post
        dispatch_post(self, u, payload, send_json)


def _graceful_reload():
    """Fork a new server process, let current one exit (survived by PTY daemon)."""
    pid = os.fork()
    if pid == 0:
        # Child — become the new server (daemon already running, no need to re-fork it)
        return
    # Parent — wait for child to signal ready, then exit
    # For now just exit and let systemd/restart handle it
    sys.exit(0)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 7777
    bind = ("127.0.0.1", port)

    # Fork the PTY daemon before serving (survives server restarts via SIGHUP)
    from backend.pty_client import ensure_daemon, daemon_pid
    asyncio.get_event_loop().run_until_complete(ensure_daemon())
    pid = daemon_pid()
    print(f"  pty_daemon: pid={pid}", flush=True)

    def shutdown_handler():
        # Clean shutdown: tell daemon to exit, then exit server
        async def _do_shutdown():
            from backend.pty_client import shutdown_daemon
            await shutdown_daemon()
        asyncio.get_event_loop().run_until_complete(_do_shutdown())
        os.kill(os.getpid(), signal.SIGTERM)

    signal.signal(signal.SIGTERM, lambda *_: shutdown_handler())
    signal.signal(signal.SIGHUP, lambda *_: _graceful_reload())

    print(f"gitswarm dashboard: http://localhost:{port}", flush=True)
    print(f"  state dir:   {STATE_DIR}", flush=True)
    print(f"  worktrees:   {WORKTREES_DIR}", flush=True)
    http.server.ThreadingHTTPServer(bind, Handler).serve_forever()


if __name__ == "__main__":
    main()
