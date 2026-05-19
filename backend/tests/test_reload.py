"""Tests for backend.reload — the auto-reload mtime tracker.

These guard the rule: editing a web/src/*.tsx file must NOT change
frontend_mtime, because that would cause the dashboard to do a full
window.location.reload() and wipe React state (active rename inputs,
PTY stream offsets, etc.) for a source-file change the browser never sees.

Run with:  python -m unittest backend.tests.test_reload
"""
import os
import tempfile
import time
import unittest
from pathlib import Path

from backend import reload as reload_mod


class FrontendMtimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gitswarm-reload-"))
        (self.tmp / "backend").mkdir()
        (self.tmp / "backend" / "routes.py").write_text("# stub")
        (self.tmp / "shared").mkdir()
        (self.tmp / "shared" / "api-contract.md").write_text("# stub")
        (self.tmp / "server.py").write_text("# stub")
        (self.tmp / "github.py").write_text("# stub")
        web = self.tmp / "web"
        (web / "src").mkdir(parents=True)
        (web / "src" / "App.tsx").write_text("// stub")
        dist = web / "dist"
        (dist / "assets").mkdir(parents=True)
        (dist / "assets" / "index.js").write_text("// stub")
        reload_mod.init(self.tmp, web, dist)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _touch(self, path: Path, future_seconds: float = 5):
        ts = time.time() + future_seconds
        os.utime(path, (ts, ts))

    def test_editing_src_file_does_not_bump_mtime(self):
        before = reload_mod.frontend_mtime()
        self._touch(self.tmp / "web" / "src" / "App.tsx", future_seconds=60)
        after = reload_mod.frontend_mtime()
        self.assertEqual(
            before, after,
            "web/src changes must not bump frontend_mtime (would cause spurious reloads)",
        )

    def test_editing_dist_bundle_does_bump_mtime(self):
        before = reload_mod.frontend_mtime()
        self._touch(self.tmp / "web" / "dist" / "assets" / "index.js", future_seconds=60)
        after = reload_mod.frontend_mtime()
        self.assertGreater(after, before)

    def test_editing_backend_does_bump_mtime(self):
        before = reload_mod.frontend_mtime()
        self._touch(self.tmp / "backend" / "routes.py", future_seconds=60)
        after = reload_mod.frontend_mtime()
        self.assertGreater(after, before)

    def test_pycache_is_ignored(self):
        pycache = self.tmp / "backend" / "__pycache__"
        pycache.mkdir()
        (pycache / "routes.cpython-312.pyc").write_text("# stub")
        before = reload_mod.frontend_mtime()
        self._touch(pycache / "routes.cpython-312.pyc", future_seconds=60)
        after = reload_mod.frontend_mtime()
        self.assertEqual(before, after, "__pycache__ must not bump frontend_mtime")

    def test_detail_reports_newest_path(self):
        dist_bundle = self.tmp / "web" / "dist" / "assets" / "index.js"
        self._touch(dist_bundle, future_seconds=120)
        mt, rel = reload_mod.frontend_mtime_detail()
        self.assertGreater(mt, 0)
        self.assertEqual(rel, "web/dist/assets/index.js")


if __name__ == "__main__":
    unittest.main()
