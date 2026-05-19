"""File change tracking for auto-reload.

Tracks only artifacts that actually affect the running server or the bundle the
browser is currently executing — built assets (web/dist) and backend Python.
Source files in web/src are intentionally NOT watched: saving a .tsx file
without rebuilding has no effect on the browser, so triggering a reload would
just wipe React state (active rename inputs, stream offsets, etc.) for nothing.
"""
from pathlib import Path


_HERE = None  # set by server.py
_WEB_DIR = None  # set by server.py
_WEB_DIST_DIR = None  # set by server.py


def init(here: Path, web_dir: Path, web_dist_dir: Path):
    global _HERE, _WEB_DIR, _WEB_DIST_DIR
    _HERE = here
    _WEB_DIR = web_dir
    _WEB_DIST_DIR = web_dist_dir


def _candidate_paths():
    candidates = [
        _HERE / "server.py",
        _HERE / "github.py",
        _HERE / "shared" / "api-contract.md",
    ]
    backend_dir = _HERE / "backend"
    if backend_dir.exists():
        for path in backend_dir.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            candidates.append(path)
    if _WEB_DIST_DIR and _WEB_DIST_DIR.exists():
        for path in _WEB_DIST_DIR.rglob("*"):
            if path.is_file():
                candidates.append(path)
    return candidates


def frontend_mtime() -> float:
    mt = 0.0
    for path in _candidate_paths():
        try:
            mt = max(mt, path.stat().st_mtime)
        except OSError:
            pass
    return mt


def frontend_mtime_detail():
    """Return (max_mtime, relative_path_of_newest_file) for diagnostics."""
    newest_mt = 0.0
    newest_path = None
    for path in _candidate_paths():
        try:
            mt = path.stat().st_mtime
        except OSError:
            continue
        if mt > newest_mt:
            newest_mt = mt
            newest_path = path
    if newest_path and _HERE:
        try:
            rel = str(newest_path.relative_to(_HERE))
        except ValueError:
            rel = str(newest_path)
    else:
        rel = ""
    return newest_mt, rel