"""Static file server for the English shuffle game site."""
from __future__ import annotations

import http.server
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class StaticRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return  # Silence default logging to stderr


def run() -> None:
    port = int(os.environ.get("PORT", "8000"))
    with http.server.ThreadingHTTPServer(("", port), StaticRequestHandler) as httpd:
        print(f"Serving on http://0.0.0.0:{port}")
        httpd.serve_forever()


if __name__ == "__main__":
    run()
