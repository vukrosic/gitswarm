"""Tests for pty_runtime — PTY session management, read/write, resize."""
import os
import tempfile
import time
import unittest
from pathlib import Path

from backend import pty_runtime


class PtyRuntimeInitTests(unittest.TestCase):
    def test_init_sets_globals(self):
        tmp = Path(tempfile.mkdtemp(prefix="gitswarm-pty-init-"))
        pty_runtime.init(tmp, "/bin/sh")
        self.assertEqual(pty_runtime.REPO_ROOT, tmp)
        self.assertEqual(pty_runtime.USER_SHELL, "/bin/sh")
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


class PtySpawnTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gitswarm-pty-spawn-"))
        pty_runtime.init(self.tmp, "/bin/sh")

    def tearDown(self):
        for s in pty_runtime.list_ptys():
            pty_runtime.delete_pty(s["sid"])
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_spawn_pty_returns_session(self):
        sess = pty_runtime.spawn_pty(["/bin/sh", "-c", "sleep 10"], label="test-spawn")
        self.assertIn("sid", sess)
        self.assertEqual(sess["label"], "test-spawn")
        self.assertTrue(sess["alive"])
        pty_runtime.delete_pty(sess["sid"])

    def test_spawn_pty_with_string_arg(self):
        sess = pty_runtime.spawn_pty("sleep 5", label="string-argv")
        self.assertIn("sid", sess)
        self.assertEqual(sess["label"], "string-argv")
        pty_runtime.delete_pty(sess["sid"])

    def test_spawn_pty_accepts_meta(self):
        sess = pty_runtime.spawn_pty(["sleep 3"], label="meta-test", meta={"issue": 42, "kind": "test"})
        self.assertEqual(sess["meta"]["issue"], 42)
        self.assertEqual(sess["meta"]["kind"], "test")
        pty_runtime.delete_pty(sess["sid"])

    def test_kill_pty_returns_true(self):
        sess = pty_runtime.spawn_pty(["sleep 10"], label="kill-me")
        ok = pty_runtime.kill_pty(sess["sid"])
        self.assertTrue(ok)
        # give the waiter thread a moment
        time.sleep(0.05)
        pty_runtime.delete_pty(sess["sid"])

    def test_kill_unknown_sid_returns_false(self):
        self.assertFalse(pty_runtime.kill_pty("no-such-sid"))


class PtyWriteReadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gitswarm-pty-io-"))
        pty_runtime.init(self.tmp, "/bin/sh")

    def tearDown(self):
        for s in pty_runtime.list_ptys():
            pty_runtime.delete_pty(s["sid"])
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_write_then_read(self):
        sess = pty_runtime.spawn_pty(["/bin/sh", "-c", "read -r LINE; echo got:$LINE; sleep 1"], label="write-test")
        time.sleep(0.1)
        ok = pty_runtime.pty_write(sess["sid"], b"hello\n")
        self.assertTrue(ok)
        # The runtime may deliver the input echo as a separate chunk from the
        # command output, so poll until "got:hello" appears.
        collected = bytearray()
        offset = 0
        deadline = time.time() + 5
        while time.time() < deadline and b"got:hello" not in collected:
            res = pty_runtime.pty_read(sess["sid"], offset, timeout=1)
            if res is None:
                break
            data, logical_len, alive, drop, reset = res
            if reset:
                collected = bytearray(data)
                offset = logical_len
            else:
                collected.extend(data)
                offset += len(data)
        self.assertIn(b"got:hello", bytes(collected))
        pty_runtime.delete_pty(sess["sid"])

    def test_write_to_dead_session_returns_false(self):
        sess = pty_runtime.spawn_pty(["/bin/sh", "-c", "echo hi"], label="dead-test")
        time.sleep(0.2)
        # session should be dead after echo completes
        pty_runtime.delete_pty(sess["sid"])
        self.assertFalse(pty_runtime.pty_write(sess["sid"], b"test"))

    def test_read_unknown_sid_returns_none(self):
        res = pty_runtime.pty_read("no-such-sid", 0, timeout=1)
        self.assertIsNone(res)

    def test_resize(self):
        sess = pty_runtime.spawn_pty(["sleep 10"], label="resize-test", rows=20, cols=80)
        ok = pty_runtime.pty_resize(sess["sid"], 40, 160)
        self.assertTrue(ok)
        updated = [s for s in pty_runtime.list_ptys() if s["sid"] == sess["sid"]][0]
        self.assertEqual(updated["rows"], 40)
        self.assertEqual(updated["cols"], 160)
        pty_runtime.delete_pty(sess["sid"])

    def test_resize_unknown_sid_returns_false(self):
        self.assertFalse(pty_runtime.pty_resize("no-such-sid", 24, 80))


class PtyLiveIssueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gitswarm-pty-live-"))
        pty_runtime.init(self.tmp, "/bin/sh")

    def tearDown(self):
        for s in pty_runtime.list_ptys():
            pty_runtime.delete_pty(s["sid"])
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_live_issue_pty_by_meta(self):
        sess = pty_runtime.spawn_pty(
            ["sleep", "30"], label="issue-session", meta={"issue": 123}
        )
        time.sleep(0.15)
        found = pty_runtime.live_issue_pty(123)
        self.assertIsNotNone(found)
        self.assertEqual(found["sid"], sess["sid"])
        pty_runtime.delete_pty(sess["sid"])

    def test_live_issue_pty_by_label(self):
        sess = pty_runtime.spawn_pty(["sleep", "30"], label="shell · #456 worktree")
        time.sleep(0.15)
        found = pty_runtime.live_issue_pty(456)
        self.assertIsNotNone(found)
        self.assertEqual(found["sid"], sess["sid"])
        pty_runtime.delete_pty(sess["sid"])

    def test_live_issue_pty_not_found(self):
        self.assertIsNone(pty_runtime.live_issue_pty(99999))


class PtyInUseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gitswarm-pty-inuse-"))
        pty_runtime.init(self.tmp, "/bin/sh")

    def tearDown(self):
        for s in pty_runtime.list_ptys():
            pty_runtime.delete_pty(s["sid"])
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_worktree_in_use(self):
        worktree = self.tmp / "worktree-dir"
        worktree.mkdir()
        pty_runtime.init(self.tmp, "/bin/sh")  # re-init with proper cwd
        sess = pty_runtime.spawn_shell_session(worktree, label="shell in worktree")
        self.assertTrue(pty_runtime.pty_in_use(worktree))
        pty_runtime.delete_pty(sess["sid"])

    def test_worktree_not_in_use(self):
        worktree = self.tmp / "other-dir"
        worktree.mkdir()
        self.assertFalse(pty_runtime.pty_in_use(worktree))

    def test_subdir_in_use(self):
        parent = self.tmp / "parent"
        sub = parent / "sub"
        sub.mkdir(parents=True)
        sess = pty_runtime.spawn_shell_session(sub, label="shell in sub")
        self.assertTrue(pty_runtime.pty_in_use(sub))
        self.assertTrue(pty_runtime.pty_in_use(parent))
        pty_runtime.delete_pty(sess["sid"])


class PtyReapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gitswarm-pty-reap-"))
        pty_runtime.init(self.tmp, "/bin/sh")

    def tearDown(self):
        for s in pty_runtime.list_ptys():
            pty_runtime.delete_pty(s["sid"])
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_reap_removes_old_dead_sessions(self):
        sess = pty_runtime.spawn_pty(["/bin/sh", "-c", "exit 0"], label="short-lived")
        # Wait for the tailer to notice the pane is dead and flip alive=False.
        deadline = time.time() + 5
        while time.time() < deadline:
            alive = [s for s in pty_runtime.list_ptys() if s["sid"] == sess["sid"]]
            if alive and not alive[0]["alive"]:
                break
            time.sleep(0.1)
        before = len(pty_runtime.list_ptys())
        self.assertEqual(before, 1)
        pty_runtime.reap_dead_ptys(max_age_dead=0)
        after = len(pty_runtime.list_ptys())
        self.assertEqual(after, 0)

    def test_reap_preserves_live_sessions(self):
        sess = pty_runtime.spawn_pty(["sleep", "60"], label="long-lived")
        time.sleep(0.05)
        pty_runtime.reap_dead_ptys(max_age_dead=600)
        sids = [s["sid"] for s in pty_runtime.list_ptys()]
        self.assertIn(sess["sid"], sids)
        pty_runtime.delete_pty(sess["sid"])


if __name__ == "__main__":
    unittest.main()