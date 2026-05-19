"""Tests for project registry helpers and project-scoped route flow."""
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from backend import projects
import github as github_mod
from backend.routes import dispatch_get, dispatch_post


class ProjectRegistryTests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.registry_root = Path(self.tmp.name)
        self.repo_root = Path.cwd().resolve()
        self.patches = [
            patch.object(projects, "REGISTRY_ROOT", self.registry_root),
            patch.object(projects, "REGISTRY_DIR", self.registry_root / ".gitswarm"),
            patch.object(projects, "REGISTRY_FILE", self.registry_root / ".gitswarm" / "projects.json"),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.tmp.cleanup()

    def test_bootstrap_adds_current_repo(self):
        project = projects.bootstrap_project(self.repo_root)
        registry = projects.list_projects()
        self.assertEqual(project["repo_root"], str(self.repo_root))
        self.assertEqual(registry["active"], project["id"])
        self.assertEqual(len(registry["projects"]), 1)

    def test_activate_project_persists(self):
        project = projects.bootstrap_project(self.repo_root)
        activated = projects.activate_project(project["id"])
        registry = projects.list_projects()
        self.assertEqual(activated["id"], project["id"])
        self.assertEqual(registry["active"], project["id"])


class ProjectRouteSmokeTests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.registry_root = Path(self.tmp.name) / "registry"
        self.repo_one = Path(self.tmp.name) / "repo-one"
        self.repo_two = Path(self.tmp.name) / "repo-two"
        self.repo_one.mkdir()
        self.repo_two.mkdir()
        subprocess.run(["git", "init"], cwd=self.repo_one, check=True, capture_output=True)
        subprocess.run(["git", "init"], cwd=self.repo_two, check=True, capture_output=True)
        self.original_repo_root = github_mod.REPO_ROOT
        self.patches = [
            patch.object(projects, "REGISTRY_ROOT", self.registry_root),
            patch.object(projects, "REGISTRY_DIR", self.registry_root / ".gitswarm"),
            patch.object(projects, "REGISTRY_FILE", self.registry_root / ".gitswarm" / "projects.json"),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        github_mod.set_repo_context(self.original_repo_root)
        for item in reversed(self.patches):
            item.stop()
        self.tmp.cleanup()

    def _handler(self):
        from unittest.mock import MagicMock

        handler = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = MagicMock()
        return handler

    def _send_json(self, handler, data, code=200):
        handler.send_response(code)
        handler._json_data = data
        return handler

    def test_add_then_activate_updates_active_project_and_repo_context(self):
        from urllib.parse import urlparse

        add_one = self._handler()
        dispatch_post(
            add_one,
            urlparse("/api/projects/add"),
            {"repo_root": str(self.repo_one), "label": "project one"},
            self._send_json,
        )
        first = add_one._json_data["project"]
        self.assertEqual(first["repo_root"], str(self.repo_one.resolve()))
        self.assertEqual(add_one._json_data["projects"]["active"], first["id"])

        add_two = self._handler()
        dispatch_post(
            add_two,
            urlparse("/api/projects/add"),
            {"repo_root": str(self.repo_two), "label": "project two"},
            self._send_json,
        )
        second = add_two._json_data["project"]
        self.assertEqual(second["repo_root"], str(self.repo_two.resolve()))
        self.assertEqual(add_two._json_data["projects"]["active"], second["id"])

        activate_one = self._handler()
        dispatch_post(
            activate_one,
            urlparse("/api/projects/activate"),
            {"project_id": first["id"]},
            self._send_json,
        )
        self.assertEqual(activate_one._json_data["project"]["id"], first["id"])
        self.assertEqual(activate_one._json_data["projects"]["active"], first["id"])
        self.assertEqual(github_mod.REPO_ROOT, self.repo_one.resolve())

        projects_get = self._handler()
        dispatch_get(projects_get, urlparse("/api/projects"), {}, self._send_json)
        self.assertEqual(projects_get._json_data["active"], first["id"])
        project_ids = [project["id"] for project in projects_get._json_data["projects"]]
        self.assertIn(first["id"], project_ids)
        self.assertIn(second["id"], project_ids)
