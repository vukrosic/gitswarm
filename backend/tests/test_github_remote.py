"""Tests for github_remote — GH API helpers and normalization."""
import json
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import github as gh_mod
from backend import github_remote as gr_mod


class GhErrorTests(unittest.TestCase):
    def test_called_process_error(self):
        from subprocess import CalledProcessError
        exc = CalledProcessError(1, ["gh", "api", "repos/x/y"], output="", stderr="resource not found")
        self.assertIn("resource not found", gr_mod.gh_error(exc))

    def test_timeout(self):
        from subprocess import TimeoutExpired
        exc = TimeoutExpired("gh api", 20)
        self.assertIn("20", gr_mod.gh_error(exc))
        self.assertIn("timed out", gr_mod.gh_error(exc))

    def test_plain_exception(self):
        self.assertEqual(gr_mod.gh_error(ValueError("bad input")), "bad input")


class TransientErrorTests(unittest.TestCase):
    _cases = [
        ("EOF", True),
        ("timed out", True),
        ("timeout", True),
        ("connection reset", True),
        ("tls handshake", True),
        ("502 Bad Gateway", True),
        ("503 Service Unavailable", True),
        ("504 Gateway Timeout", True),
        ("not found", False),
        ("unauthorized", False),
        ("rate limit", False),
    ]

    def test_is_transient(self):
        for msg, expected in self._cases:
            with self.subTest(msg=msg):
                self.assertEqual(gr_mod.is_transient_gh_error(msg), expected)


class TextPreviewTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(gr_mod._text_preview(""), "")
        self.assertEqual(gr_mod._text_preview(None), "")

    def test_strips_newlines(self):
        text = "line one\n\nline two"
        result = gr_mod._text_preview(text, limit=100)
        self.assertNotIn("\n", result)

    def test_truncates_long_text(self):
        text = "a" * 300
        result = gr_mod._text_preview(text, limit=20)
        self.assertEqual(len(result), 20)
        self.assertTrue(result.endswith("…"))

    def test_uses_first_paragraph(self):
        text = "first paragraph here\n\nsecond paragraph"
        result = gr_mod._text_preview(text, limit=200)
        self.assertTrue(result.startswith("first paragraph"))


class IssueLabelSuggestionsTests(unittest.TestCase):
    def test_suggest_agent_friendly(self):
        labels = gr_mod._issue_label_suggestions("add a terminal feature", "")
        self.assertIn("agent-friendly", labels)

    def test_suggest_claim_next(self):
        labels = gr_mod._issue_label_suggestions("fix the bug", "implement this")
        self.assertIn("claim-next", labels)

    def test_suggest_needs_validation(self):
        labels = gr_mod._issue_label_suggestions("maybe we should explore", "")
        self.assertIn("needs-validation", labels)

    def test_suggest_good_first_issue(self):
        labels = gr_mod._issue_label_suggestions("", "a small beginner task")
        self.assertIn("good first issue", labels)

    def test_max_three(self):
        title = "fix small agent terminal issue maybe should we explore"
        labels = gr_mod._issue_label_suggestions(title, "")
        self.assertLessEqual(len(labels), 3)


class NormalizeMilestoneTests(unittest.TestCase):
    def test_none_input(self):
        self.assertIsNone(gr_mod._normalize_milestone(None))

    def test_non_dict(self):
        self.assertIsNone(gr_mod._normalize_milestone("string"))

    def test_known_fields(self):
        raw = {
            "number": 5,
            "title": "v1.0",
            "description": "release",
            "state": "open",
            "open_issues": 3,
            "closed_issues": 7,
            "due_on": "2025-01-01T00:00:00Z",
            "created_at": "2024-01-01",
            "updated_at": "2024-06-01",
            "url": "https://github.com/x/y/milestones/5",
            "html_url": "https://github.com/x/y/milestones/5",
        }
        m = gr_mod._normalize_milestone(raw)
        self.assertEqual(m["number"], 5)
        self.assertEqual(m["title"], "v1.0")
        self.assertEqual(m["open_issues"], 3)
        self.assertEqual(m["closed_issues"], 7)

    def test_camelcase_alias(self):
        raw = {"openIssues": 10, "closedIssues": 5, "dueOn": "2025-01-01"}
        m = gr_mod._normalize_milestone(raw)
        self.assertEqual(m["open_issues"], 10)
        self.assertEqual(m["closed_issues"], 5)
        self.assertEqual(m["due_on"], "2025-01-01")


class NormalizeCommentTests(unittest.TestCase):
    def test_none(self):
        self.assertIsNone(gr_mod._normalize_comment(None))

    def test_user_field(self):
        raw = {"id": 1, "user": {"login": "alice"}, "body": "hello", "html_url": "https://gh.com/c1"}
        c = gr_mod._normalize_comment(raw)
        self.assertEqual(c["author"], "alice")

    def test_author_field(self):
        raw = {"id": 2, "author": {"login": "bob"}, "body": "hi", "url": "https://gh.com/c2"}
        c = gr_mod._normalize_comment(raw)
        self.assertEqual(c["author"], "bob")

    def test_plain_user(self):
        raw = {"id": 3, "user": "charlie", "body": "yo"}
        c = gr_mod._normalize_comment(raw)
        self.assertEqual(c["author"], "charlie")


class NormalizeReviewTests(unittest.TestCase):
    def test_none(self):
        self.assertIsNone(gr_mod._normalize_review(None))

    def test_roundtrip(self):
        raw = {
            "id": 100,
            "user": {"login": "reviewer1"},
            "state": "APPROVED",
            "body": "lgtm",
            "html_url": "https://gh.com/r100",
            "submitted_at": "2024-01-01T00:00:00Z",
        }
        r = gr_mod._normalize_review(raw)
        self.assertEqual(r["id"], 100)
        self.assertEqual(r["author"], "reviewer1")
        self.assertEqual(r["state"], "APPROVED")


class ReviewerVerdictTests(unittest.TestCase):
    def test_extracts_verdict_block(self):
        text = """noise\n# Reviewer-agent verdict\n**Model:** codex\n**Verdict:** approve\n\n## Verdict reasoning\nLooks good.\n──── exit banner"""
        body = gh_mod.extract_reviewer_verdict(text)
        self.assertIn("Reviewer-agent verdict", body)
        self.assertNotIn("exit banner", body)

    def test_maps_approve(self):
        text = "# Reviewer-agent verdict\n**Verdict:** approve\n"
        self.assertEqual(gh_mod.review_verdict_mode(text), "approve")

    def test_maps_reject_to_request_changes(self):
        text = "# Reviewer-agent verdict\n**Verdict:** reject\n"
        self.assertEqual(gh_mod.review_verdict_mode(text), "request-changes")


class LocalCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        gr_mod.init(root, root / ".gitswarm" / "state")
        gr_mod.invalidate_caches()

    def _set_subprocess_run(self, payload, expected_args_prefix):
        def fake_run(args, capture_output=False, text=False, timeout=None, check=None):
            if args[:len(expected_args_prefix)] != expected_args_prefix:
                raise AssertionError(f"unexpected command: {args}")
            return CompletedProcess(args, 0, stdout=json.dumps(payload), stderr="")
        return fake_run

    def test_list_issues_uses_disk_cache_on_cold_start(self):
        payload = [
            {
                "number": 7,
                "title": "cached issue",
                "body": "body text",
                "labels": [],
                "url": "https://example.com/issues/7",
                "author": {"login": "alice"},
                "assignees": [],
                "comments": [],
                "createdAt": "2025-01-01T00:00:00Z",
                "updatedAt": "2025-01-02T00:00:00Z",
                "state": "OPEN",
                "milestone": None,
            }
        ]
        with patch.object(gr_mod.subprocess, "run", side_effect=self._set_subprocess_run(payload, ["gh", "issue", "list"])):
            first = gr_mod.list_issues()
        self.assertEqual(first[0]["number"], 7)
        cache_file = Path(self.tmp.name) / ".gitswarm" / "state" / ".gh-cache" / "issues.json"
        self.assertTrue(cache_file.exists())

        gr_mod._ISSUES_CACHE = {"ts": 0, "data": None}
        with patch.object(gr_mod.subprocess, "run", side_effect=AssertionError("should not hit gh again")):
            second = gr_mod.list_issues()
        self.assertEqual(second[0]["number"], 7)
        self.assertEqual(second[0]["summary"], "body text")

    def test_list_prs_uses_disk_cache_on_cold_start(self):
        payload = [
            {
                "number": 12,
                "title": "cached pr",
                "body": "PR body",
                "isDraft": False,
                "headRefName": "feature",
                "baseRefName": "main",
                "url": "https://example.com/pull/12",
                "reviewDecision": "",
                "mergeable": "MERGEABLE",
                "labels": [],
                "statusCheckRollup": [],
                "comments": [],
                "author": {"login": "bob"},
                "createdAt": "2025-01-01T00:00:00Z",
                "updatedAt": "2025-01-02T00:00:00Z",
            }
        ]
        with patch.object(gr_mod.subprocess, "run", side_effect=self._set_subprocess_run(payload, ["gh", "pr", "list"])):
            first = gr_mod.list_prs()
        self.assertEqual(first[0]["number"], 12)
        cache_file = Path(self.tmp.name) / ".gitswarm" / "state" / ".gh-cache" / "prs.json"
        self.assertTrue(cache_file.exists())

        gr_mod._PRS_CACHE = {"ts": 0, "data": None}
        with patch.object(gr_mod.subprocess, "run", side_effect=AssertionError("should not hit gh again")):
            second = gr_mod.list_prs()
        self.assertEqual(second[0]["number"], 12)
        self.assertEqual(second[0]["summary"], "PR body")


if __name__ == "__main__":
    unittest.main()
