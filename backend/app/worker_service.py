from __future__ import annotations

import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from app.worker import run_worker


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path not in {"/", "/health", "/healthz", "/ready"}:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"ok","service":"worker"}')

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def start_health_server() -> None:
    port = int(os.getenv("PORT", "8080"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


def main() -> None:
    thread = threading.Thread(target=start_health_server, daemon=True)
    thread.start()
    run_worker()


if __name__ == "__main__":
    main()
