"""Project registry helpers for the gitswarm dashboard."""
import hashlib
import json
import re
import subprocess
from pathlib import Path


REGISTRY_ROOT = Path.cwd().resolve()
REGISTRY_DIR = REGISTRY_ROOT / ".gitswarm"
REGISTRY_FILE = REGISTRY_DIR / "projects.json"


def _default_registry():
    return {"version": 1, "active": "", "projects": []}


def _ensure_dir(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def _read_json(file: Path):
    try:
        return json.loads(file.read_text())
    except Exception:
        return None


def _write_json(file: Path, payload):
    _ensure_dir(file)
    file.write_text(f"{json.dumps(payload, indent=2)}\n")


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


def _repo_root(repo_root) -> Path:
    root = Path(repo_root).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"repo does not exist: {root}")
    return root


def _git_toplevel(repo_root: Path) -> Path:
    res = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    return Path(res.stdout.strip()).resolve()


def _github_slug(repo_root: Path) -> str:
    res = subprocess.run(
        ["git", "-C", str(repo_root), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    if res.returncode != 0:
        return ""
    url = (res.stdout or "").strip()
    if not url:
        return ""
    match = re.search(r"github\.com[:/]([^/]+/.+?)(?:\.git)?$", url.rstrip("/"))
    return match.group(1) if match else ""


def project_id(repo_root) -> str:
    root = _repo_root(repo_root)
    digest = hashlib.sha1(str(root).encode("utf-8")).hexdigest()[:8]
    return f"{_slugify(root.name) or 'project'}-{digest}"


def inspect_project(repo_root, label=None):
    root = _git_toplevel(_repo_root(repo_root))
    github_slug = _github_slug(root)
    return {
        "id": project_id(root),
        "label": label or github_slug or root.name,
        "repo_root": str(root),
        "repo_name": root.name,
        "github_slug": github_slug,
        "state_dir": str(root / ".gitswarm" / "state"),
        "worktree_dir": str(root / ".agent-worktrees"),
        "exists": root.exists(),
    }


def read_registry():
    data = _read_json(REGISTRY_FILE)
    if not isinstance(data, dict):
        data = _default_registry()
    data.setdefault("version", 1)
    data.setdefault("active", "")
    data.setdefault("projects", [])
    if not isinstance(data["projects"], list):
        data["projects"] = []
    return data


def write_registry(data):
    payload = {
        "version": int(data.get("version", 1) or 1),
        "active": str(data.get("active") or ""),
        "projects": list(data.get("projects") or []),
    }
    _write_json(REGISTRY_FILE, payload)
    return payload


def _normalize_projects(projects):
    out = []
    for raw in projects:
        if not isinstance(raw, dict):
            continue
        repo_root = raw.get("repo_root") or ""
        if not repo_root:
            continue
        try:
            current = inspect_project(repo_root, label=raw.get("label") or "")
        except Exception:
            current = {
                "id": str(raw.get("id") or project_id(repo_root)),
                "label": raw.get("label") or Path(repo_root).name,
                "repo_root": str(Path(repo_root).expanduser().resolve()),
                "repo_name": raw.get("repo_name") or Path(repo_root).name,
                "github_slug": raw.get("github_slug") or "",
                "state_dir": str(Path(repo_root).expanduser().resolve() / ".gitswarm" / "state"),
                "worktree_dir": str(Path(repo_root).expanduser().resolve() / ".agent-worktrees"),
                "exists": Path(repo_root).expanduser().resolve().exists(),
            }
        current["id"] = str(raw.get("id") or current["id"])
        current["label"] = str(raw.get("label") or current["label"] or current["repo_name"])
        current["active"] = bool(raw.get("active", False))
        current["updated_at"] = raw.get("updated_at") or ""
        current["created_at"] = raw.get("created_at") or ""
        out.append(current)
    return out


def list_projects():
    reg = read_registry()
    projects = _normalize_projects(reg.get("projects", []))
    active = str(reg.get("active") or "")
    if active and not any(project["id"] == active for project in projects):
        active = ""
    for project in projects:
        project["active"] = project["id"] == active
    return {"active": active, "projects": projects}


def upsert_project(repo_root, label=None, activate=False):
    root = _git_toplevel(_repo_root(repo_root))
    reg = read_registry()
    projects = _normalize_projects(reg.get("projects", []))
    target = inspect_project(root, label=label)
    existing = [p for p in projects if p["id"] == target["id"]]
    if existing:
        current = existing[0]
        current.update(target)
        current["label"] = label or current.get("label") or target["label"]
    else:
        current = {
            **target,
            "created_at": "",
            "updated_at": "",
            "active": False,
        }
        projects.append(current)
    if activate:
        reg["active"] = current["id"]
    elif not reg.get("active"):
        reg["active"] = current["id"]
    reg["projects"] = projects
    write_registry(reg)
    return current


def bootstrap_project(repo_root):
    """Ensure the current host repo is present in the registry."""
    current = upsert_project(repo_root, activate=False)
    reg = read_registry()
    active = str(reg.get("active") or "")
    if not active:
        reg["active"] = current["id"]
        write_registry(reg)
    return current


def activate_project(project_id_value):
    reg = read_registry()
    projects = _normalize_projects(reg.get("projects", []))
    if not projects:
        return None
    for project in projects:
        project["active"] = project["id"] == project_id_value
        if project["active"]:
            reg["active"] = project["id"]
    if not any(project["id"] == project_id_value for project in projects):
        return None
    reg["projects"] = projects
    write_registry(reg)
    return next(project for project in projects if project["id"] == project_id_value)


def get_active_project():
    reg = read_registry()
    projects = _normalize_projects(reg.get("projects", []))
    active = str(reg.get("active") or "")
    if active:
        for project in projects:
            if project["id"] == active:
                project["active"] = True
                return project
    if projects:
        projects[0]["active"] = True
        reg["active"] = projects[0]["id"]
        reg["projects"] = projects
        write_registry(reg)
        return projects[0]
    return None

