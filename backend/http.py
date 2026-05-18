"""HTTP helpers for route handlers."""
import json


def send_json(handler, obj, status=200):
    body = json.dumps(obj).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def read_json_body(handler, content_length):
    if not content_length:
        return {}
    try:
        return json.loads(handler.rfile.read(content_length).decode() or "{}")
    except json.JSONDecodeError:
        return None


def bad_request(handler, message="bad request"):
    send_json(handler, {"error": message}, 400)


def server_error(handler, message="internal error"):
    send_json(handler, {"error": message}, 500)


def not_found(handler, message="not found"):
    send_json(handler, {"error": message}, 404)