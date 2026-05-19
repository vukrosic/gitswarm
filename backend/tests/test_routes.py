"""Tests for routes — path dispatch, parameter validation, and HTTP response helpers."""
import unittest
from unittest.mock import MagicMock


class QueryValueTests(unittest.TestCase):
    def test_returns_default_for_missing(self):
        from backend.routes import _query_value
        self.assertEqual(_query_value({}, "foo"), "")
        self.assertEqual(_query_value({}, "foo", "default"), "default")

    def test_returns_value(self):
        from backend.routes import _query_value
        qs = {"name": ["alice"]}
        self.assertEqual(_query_value(qs, "name"), "alice")

    def test_returns_first_of_list(self):
        from backend.routes import _query_value
        qs = {"name": ["alice", "bob"]}
        self.assertEqual(_query_value(qs, "name"), "alice")


class DispatchGetTests(unittest.TestCase):
    def _fake_handler(self):
        h = MagicMock()
        h.send_response = MagicMock()
        h.send_header = MagicMock()
        h.end_headers = MagicMock()
        return h

    def _send_json_fn(self, handler, data, code=200):
        handler.send_response(code)
        for k, v in data.items():
            handler._json_data = data
        return handler

    def test_issue_meta_missing_num(self):
        from backend.routes import dispatch_get
        from urllib.parse import urlparse, parse_qs
        u = urlparse("/api/issue")
        qs = parse_qs("")
        h = self._fake_handler()
        result = dispatch_get(h, u, qs, self._send_json_fn)
        # no return → 404 sent for unrecognized path; issue endpoint with no num → error
        # re-check: the dispatch uses qs.get which returns empty list for missing key
        # so _handle_issue_meta gets ValueError from int("") and sends 400
        self.assertEqual(h.send_response.call_count, 1)
        self.assertEqual(h._json_data.get("error"), "bad num")

    def test_issue_meta_bad_num(self):
        from backend.routes import dispatch_get
        from urllib.parse import urlparse, parse_qs
        u = urlparse("/api/issue")
        qs = parse_qs("num=abc")
        h = self._fake_handler()
        dispatch_get(h, u, qs, self._send_json_fn)
        self.assertEqual(h._json_data.get("error"), "bad num")

    def test_issue_meta_out_of_range(self):
        from backend.routes import dispatch_get
        from urllib.parse import urlparse, parse_qs
        u = urlparse("/api/issue")
        qs = parse_qs("num=99999")
        h = self._fake_handler()
        dispatch_get(h, u, qs, self._send_json_fn)
        self.assertEqual(h._json_data.get("error"), "bad num")

    def test_pr_meta_bad_num(self):
        from backend.routes import dispatch_get
        from urllib.parse import urlparse, parse_qs
        u = urlparse("/api/pr")
        qs = parse_qs("num=-1")
        h = self._fake_handler()
        dispatch_get(h, u, qs, self._send_json_fn)
        self.assertEqual(h._json_data.get("error"), "bad num")

    def test_pr_diff_bad_num(self):
        from backend.routes import dispatch_get
        from urllib.parse import urlparse, parse_qs
        u = urlparse("/api/pr/diff")
        qs = parse_qs("num=abc")
        h = self._fake_handler()
        dispatch_get(h, u, qs, self._send_json_fn)
        self.assertEqual(h._json_data.get("error"), "bad num")

    def test_unknown_path_returns_404(self):
        from backend.routes import dispatch_get
        from urllib.parse import urlparse, parse_qs
        u = urlparse("/api/nonexistent")
        qs = parse_qs("")
        h = self._fake_handler()
        dispatch_get(h, u, qs, self._send_json_fn)
        h.send_response.assert_called_with(404)


class DispatchPostTests(unittest.TestCase):
    def _send_json_fn(self, handler, data, code=200):
        handler.send_response(code)
        handler._json_data = data
        return handler

    def test_launch_missing_issue(self):
        from backend.routes import dispatch_post
        from urllib.parse import urlparse
        u = urlparse("/api/launch")
        h = MagicMock()
        h.send_response = MagicMock()
        h.send_header = MagicMock()
        h.end_headers = MagicMock()
        payload = {}
        dispatch_post(h, u, payload, self._send_json_fn)
        self.assertEqual(h._json_data.get("error"), "issue must be int")

    def test_launch_bad_issue_type(self):
        from backend.routes import dispatch_post
        from urllib.parse import urlparse
        u = urlparse("/api/launch")
        h = MagicMock()
        h.send_response = MagicMock()
        h.send_header = MagicMock()
        h.end_headers = MagicMock()
        dispatch_post(h, u, {"issue": "not-an-int"}, self._send_json_fn)
        self.assertEqual(h._json_data.get("error"), "issue must be int")

    def test_launch_issue_out_of_range(self):
        from backend.routes import dispatch_post
        from urllib.parse import urlparse
        u = urlparse("/api/launch")
        h = MagicMock()
        h.send_response = MagicMock()
        h.send_header = MagicMock()
        h.end_headers = MagicMock()
        dispatch_post(h, u, {"issue": 0}, self._send_json_fn)
        self.assertEqual(h._json_data.get("error"), "bad issue number")

    def test_pty_rename_requires_sid(self):
        from backend.routes import dispatch_post
        from urllib.parse import urlparse
        u = urlparse("/api/pty/rename")
        h = MagicMock()
        h.send_response = MagicMock()
        h.send_header = MagicMock()
        h.end_headers = MagicMock()
        dispatch_post(h, u, {"sid": "", "label": "new-label"}, self._send_json_fn)
        self.assertEqual(h._json_data.get("error"), "sid is required")

    def test_pty_input_requires_string_data(self):
        from backend.routes import dispatch_post
        from urllib.parse import urlparse
        u = urlparse("/api/pty/input")
        h = MagicMock()
        h.send_response = MagicMock()
        h.send_header = MagicMock()
        h.end_headers = MagicMock()
        dispatch_post(h, u, {"sid": "abc123", "data": 12345}, self._send_json_fn)
        self.assertEqual(h._json_data.get("error"), "data must be string")

    def test_state_cleanup_bad_stale_days(self):
        from backend.routes import dispatch_post
        from urllib.parse import urlparse
        u = urlparse("/api/state/cleanup")
        h = MagicMock()
        h.send_response = MagicMock()
        h.send_header = MagicMock()
        h.end_headers = MagicMock()
        dispatch_post(h, u, {"stale_days": "not-an-int"}, self._send_json_fn)
        self.assertEqual(h._json_data.get("error"), "stale_days must be int")

    def test_issue_create_requires_title(self):
        from backend.routes import dispatch_post
        from urllib.parse import urlparse
        u = urlparse("/api/issue/create")
        h = MagicMock()
        h.send_response = MagicMock()
        h.send_header = MagicMock()
        h.end_headers = MagicMock()
        dispatch_post(h, u, {"title": ""}, self._send_json_fn)
        self.assertEqual(h._json_data.get("error"), "title is required")


class PtyStreamOffsetTests(unittest.TestCase):
    def _send_json_fn(self, handler, data, code=200):
        handler.send_response(code)
        handler._json_data = data
        return handler

    def test_bad_offset(self):
        from backend.routes import dispatch_get
        from urllib.parse import urlparse, parse_qs
        u = urlparse("/api/pty/stream")
        qs = parse_qs("sid=abc123&offset=not-int")
        h = MagicMock()
        h.send_response = MagicMock()
        h.send_header = MagicMock()
        h.end_headers = MagicMock()
        dispatch_get(h, u, qs, self._send_json_fn)
        self.assertEqual(h._json_data.get("error"), "bad offset")


class PtyResizeTests(unittest.TestCase):
    def _send_json_fn(self, handler, data, code=200):
        handler.send_response(code)
        handler._json_data = data
        return handler

    def test_rows_not_int(self):
        from backend.routes import dispatch_post
        from urllib.parse import urlparse
        u = urlparse("/api/pty/resize")
        h = MagicMock()
        h.send_response = MagicMock()
        h.send_header = MagicMock()
        h.end_headers = MagicMock()
        dispatch_post(h, u, {"sid": "abc", "rows": "x", "cols": "y"}, self._send_json_fn)
        self.assertEqual(h._json_data.get("error"), "rows/cols must be int")


class FileReadTests(unittest.TestCase):
    def _send_json_fn(self, handler, data, code=200):
        handler.send_response(code)
        handler._json_data = data
        return handler

    def test_name_with_dotdot_rejected(self):
        from backend.routes import dispatch_get
        from urllib.parse import urlparse, parse_qs
        u = urlparse("/api/file")
        qs = parse_qs("name=../../etc/passwd")
        h = MagicMock()
        h.send_response = MagicMock()
        h.send_header = MagicMock()
        h.end_headers = MagicMock()
        dispatch_get(h, u, qs, self._send_json_fn)
        self.assertEqual(h._json_data.get("error"), "bad name")

    def test_name_with_slash_rejected(self):
        from backend.routes import dispatch_get
        from urllib.parse import urlparse, parse_qs
        u = urlparse("/api/file")
        qs = parse_qs("name=some/file")
        h = MagicMock()
        h.send_response = MagicMock()
        h.send_header = MagicMock()
        h.end_headers = MagicMock()
        dispatch_get(h, u, qs, self._send_json_fn)
        self.assertEqual(h._json_data.get("error"), "bad name")


if __name__ == "__main__":
    unittest.main()