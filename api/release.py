"""Anonymous source-revision contract for portfolio publication."""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler


def release_payload() -> dict[str, str]:
    return {
        "status": "live",
        "source_sha": os.environ.get("VERCEL_GIT_COMMIT_SHA", ""),
    }


class handler(BaseHTTPRequestHandler):
    server_version = "CRTRelease/1.0"
    sys_version = ""

    def do_GET(self) -> None:
        body = json.dumps(release_payload()).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
