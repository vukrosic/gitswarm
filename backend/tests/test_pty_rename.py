"""Tests for pty_rename — verifies a renamed PTY session reports its new
label through list_ptys(), so the next snapshot poll cannot silently revert
the label in the dashboard.

Run with:  python -m unittest backend.tests.test_pty_rename
"""
import os
import tempfile
import time
import unittest
from pathlib import Path

from backend import pty_runtime


class PtyRenameTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gitswarm-pty-"))
        pty_runtime.init(self.tmp, "/bin/sh")
        # spawn a long-ish process so the session stays alive for the test
        sess = pty_runtime.spawn_pty(["/bin/sh", "-c", "sleep 5"], label="original-label")
        self.sid = sess["sid"]
        # let the runtime register the session
        time.sleep(0.05)
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        try:
            pty_runtime.delete_pty(self.sid)
        except Exception:
            pass
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_rename_updates_list_ptys_label(self):
        before = [s for s in pty_runtime.list_ptys() if s["sid"] == self.sid][0]
        self.assertEqual(before["label"], "original-label")

        ok = pty_runtime.pty_rename(self.sid, "renamed-label")
        self.assertTrue(ok)

        after = [s for s in pty_runtime.list_ptys() if s["sid"] == self.sid][0]
        self.assertEqual(
            after["label"], "renamed-label",
            "rename must be visible in the next list_ptys() poll",
        )

    def test_rename_persists_across_multiple_polls(self):
        pty_runtime.pty_rename(self.sid, "stable-name")
        for _ in range(3):
            time.sleep(0.05)
            after = [s for s in pty_runtime.list_ptys() if s["sid"] == self.sid][0]
            self.assertEqual(after["label"], "stable-name")

    def test_rename_unknown_sid_returns_false(self):
        self.assertFalse(pty_runtime.pty_rename("does-not-exist", "x"))


if __name__ == "__main__":
    unittest.main()
