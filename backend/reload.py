"""File change tracking for auto-reload."""
from pathlib import Path


_HERE = None  # set by server.py
_WEB_DIR = None  # set by server.py
_WEB_DIST_DIR = None  # set by server.py


def init(here: Path, web_dir: Path, web_dist_dir: Path):
    global _HERE, _WEB_DIR, _WEB_DIST_DIR
    _HERE = here
    _WEB_DIR = web_dir
    _WEB_DIST_DIR = web_dist_dir


def frontend_mtime() -> float:
    candidates = [
        _HERE / "server.py",
        _HERE / "github.py",
        _HERE / "shared" / "api-contract.md",
    ]
    # Backend Python files
    backend_dir = _HERE / "backend"
    if backend_dir.exists():
        for path in backend_dir.rglob("*.py"):
            candidates.append(path)
    # Web source and build artifacts
    if _WEB_DIR:
        for path in (
            _WEB_DIR / "index.html",
            _WEB_DIR / "package.json",
            _WEB_DIR / "tsconfig.json",
            _WEB_DIR / "vite.config.ts",
        ):
            candidates.append(path)
        src_dir = _WEB_DIR / "src"
        if src_dir.exists():
            for path in src_dir.rglob("*"):
                if path.is_file():
                    candidates.append(path)
    if _WEB_DIST_DIR and _WEB_DIST_DIR.exists():
        for path in _WEB_DIST_DIR.rglob("*"):
            if path.is_file():
                candidates.append(path)
    mt = 0.0
    for path in candidates:
        try:
            mt = max(mt, path.stat().st_mtime)
        except OSError:
            pass
    return mt