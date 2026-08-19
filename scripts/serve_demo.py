#!/usr/bin/env python3
# ruff: noqa: I001
"""Serve the verified public workbench and local masked data on loopback."""

from __future__ import annotations

import argparse
import json
import os
import sys
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.records import QueryError, payload


DIST = ROOT / "dist"
HOST = "127.0.0.1"
os.environ.setdefault("CRT_DATA_DIR", str(ROOT / "data/public/full-data"))


class DemoHandler(SimpleHTTPRequestHandler):
    server_version = "CRTStatic"
    sys_version = ""

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/records":
            super().do_GET()
            return
        try:
            body = json.dumps(
                payload(parse_qs(parsed.query)), ensure_ascii=False
            ).encode("utf-8")
            status = HTTPStatus.OK
        except (QueryError, TypeError, ValueError) as error:
            body = json.dumps(
                {"error": str(error), "recovery": "Reset the record filters and retry."}
            ).encode("utf-8")
            status = HTTPStatus.BAD_REQUEST
        except (OSError, RuntimeError) as error:
            print(f"record query failed: {type(error).__name__}")
            body = json.dumps(
                {
                    "error": "The full-data partition could not be queried.",
                    "recovery": "Rebuild the public full-data release and retry.",
                }
            ).encode("utf-8")
            status = HTTPStatus.BAD_GATEWAY
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'",
        )
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        super().end_headers()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Serve the local CRT demo.")
    parser.add_argument(
        "--port", type=int, default=8000, help="Loopback port to bind (default: 8000)."
    )
    args = parser.parse_args()
    if not (DIST / "manifest.json").is_file():
        raise SystemExit("Release bundle missing. Run scripts/build_release.py first.")
    handler = partial(DemoHandler, directory=str(DIST))
    server = ThreadingHTTPServer((HOST, args.port), handler)
    print(f"CRT public twin: http://{HOST}:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCRT demo stopped.")
    finally:
        server.server_close()
