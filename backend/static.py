"""Static file serving for the React frontend."""
import mimetypes
from pathlib import Path


WEB_DIR = None  # set by server.py
WEB_DIST_DIR = None  # set by server.py
WEB_INDEX_HTML = None  # set by server.py


def init(web_dir: Path, web_dist_dir: Path, web_index_html: Path):
    global WEB_DIR, WEB_DIST_DIR, WEB_INDEX_HTML
    WEB_DIR = web_dir
    WEB_DIST_DIR = web_dist_dir
    WEB_INDEX_HTML = web_index_html


def _serve_file(handler, path: Path) -> bool:
    try:
        data = path.read_bytes()
    except OSError:
        return False
    mime, _ = mimetypes.guess_type(str(path))
    handler.send_response(200)
    handler.send_header("Content-Type", mime or "application/octet-stream")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)
    return True


def serve_static(handler, rel_path: str) -> bool:
    """Serve a file from web/dist/ if it exists and is safe."""
    if WEB_INDEX_HTML is None or not WEB_INDEX_HTML.exists():
        return False
    if rel_path in ("", "index.html"):
        return _serve_file(handler, WEB_INDEX_HTML)
    candidate = (WEB_DIST_DIR / rel_path).resolve()
    try:
        candidate.relative_to(WEB_DIST_DIR.resolve())
    except ValueError:
        candidate = WEB_INDEX_HTML
    if candidate.exists() and candidate.is_file() and candidate != WEB_INDEX_HTML:
        if _serve_file(handler, candidate):
            return True
    if "." not in Path(rel_path).name:
        return _serve_file(handler, WEB_INDEX_HTML)
    return False


def serve_missing_build(handler) -> bool:
    body = (
        "<!doctype html><meta charset=\"utf-8\">"
        "<title>gitswarm frontend build missing</title>"
        "<style>body{font:16px sans-serif;margin:3rem;line-height:1.5}"
        "code{background:#eee;padding:.15rem .35rem;border-radius:4px}</style>"
        "<h1>gitswarm frontend build missing</h1>"
        "<p>Run <code>npm --prefix web install</code> and "
        "<code>npm --prefix web run build</code>, then restart the dashboard.</p>"
    ).encode()
    handler.send_response(503)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)
    return True


def maybe_serve_frontend(handler, request_path: str) -> bool:
    """Return True if the request was handled as a frontend route."""
    if not request_path.startswith("/api/"):
        if WEB_INDEX_HTML is None or not WEB_INDEX_HTML.exists():
            rel_path = request_path.lstrip("/")
            if request_path in ("/", "/index.html") or "." not in Path(rel_path).name:
                return serve_missing_build(handler)
            return False
        if serve_static(handler, request_path.lstrip("/")):
            return True
    if request_path in ("/", "/index.html"):
        if WEB_INDEX_HTML and WEB_INDEX_HTML.exists():
            return _serve_file(handler, WEB_INDEX_HTML)
    return False
