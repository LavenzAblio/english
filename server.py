"""Minimal web server for the English guessing game."""
from __future__ import annotations

import html
import http.server
import os
import socketserver
import urllib.parse
from typing import Optional

from algorithm import ShuffleResult, create_shuffle, load_history, save_entry


class ShuffleRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler API)
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/":
            self.send_error(404, "Not Found")
            return

        params = urllib.parse.parse_qs(parsed.query)
        result: Optional[ShuffleResult] = None
        history = load_history()
        if "index" in params:
            try:
                idx = int(params["index"][0])
                result = history[idx]
            except (ValueError, IndexError):
                pass
        self._respond_page(result=result, history=history)

    def do_POST(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler API)
        if self.path != "/shuffle":
            self.send_error(404, "Not Found")
            return

        length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(length).decode("utf-8", errors="ignore")
        params = urllib.parse.parse_qs(payload)
        text = params.get("text", [""])[0].strip()
        if not text:
            history = load_history()
            self._respond_page(error="문장을 입력해 주세요.", history=history)
            return

        result = create_shuffle(text)
        save_entry(result)
        history = load_history()
        self._respond_page(result=result, history=history)

    def _respond_page(
        self,
        *,
        result: Optional[ShuffleResult] = None,
        history: list[ShuffleResult] | None = None,
        error: str | None = None,
    ) -> None:
        history = history if history is not None else load_history()
        body = self._render_html(result=result, history=history, error=error)
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _render_html(
        self,
        *,
        result: Optional[ShuffleResult],
        history: list[ShuffleResult],
        error: str | None,
    ) -> str:
        header = "<h1>영문 무작위 배열 게임</h1>"
        form = """
        <form action=\"/shuffle\" method=\"POST\">
            <label for=\"text\">영문을 입력하세요:</label><br />
            <textarea id=\"text\" name=\"text\" rows=\"3\" cols=\"60\"></textarea><br />
            <button type=\"submit\">섞기</button>
        </form>
        """

        result_block = ""
        if result:
            result_block = f"""
            <section class=\"result\">
                <h2>결과</h2>
                <p><strong>원문:</strong> {html.escape(result.original_text)}</p>
                <p><strong>정규화 문장:</strong> {html.escape(result.normalized_text)}</p>
                <p><strong>무작위 힌트:</strong> {html.escape(result.hint_string())}</p>
                <p><strong>문장부호 위치 표시:</strong> {html.escape(result.punctuation_mask())}</p>
            </section>
            """

        history_items = "".join(
            f"<li><a href=\"/?index={len(history) - 1 - idx}\">{html.escape(item.original_text)}</a></li>"
            for idx, item in enumerate(reversed(history))
        )
        history_block = f"""
        <section class=\"history\">
            <h2>이전 문장</h2>
            <ul>{history_items or '<li>기록이 없습니다.</li>'}</ul>
        </section>
        """

        error_block = f"<p class=\"error\">{html.escape(error)}</p>" if error else ""

        style = """
        <style>
            body { font-family: sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; }
            textarea { width: 100%; }
            .result, .history { border: 1px solid #ccc; padding: 1rem; margin-top: 1rem; border-radius: 8px; }
            .error { color: #b00020; }
            ul { list-style: disc; padding-left: 1.5rem; }
        </style>
        """

        return f"""
        <!doctype html>
        <html lang=\"ko\">\n<head>\n<meta charset=\"utf-8\" />\n{style}\n<title>영문 무작위 배열</title>\n</head>\n<body>\n{header}\n{error_block}\n{form}\n{result_block}\n{history_block}\n</body>\n</html>
        """

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return  # Silence default logging to stderr


def run() -> None:
    port = int(os.environ.get("PORT", "8000"))
    with socketserver.TCPServer(("", port), ShuffleRequestHandler) as httpd:
        print(f"Serving on http://0.0.0.0:{port}")
        httpd.serve_forever()


if __name__ == "__main__":
    run()
