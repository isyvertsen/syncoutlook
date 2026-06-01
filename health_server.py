"""Lightweight health-check HTTP server for the sync scheduler.

The scheduler is a long-running worker with no HTTP surface, so orchestrators
(Coolify, Docker, k8s) cannot tell whether it is alive. This exposes a tiny
``/health`` endpoint they can probe. It uses only the standard library and runs
in a daemon thread, so it never blocks the scheduler loop.
"""

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

logger = logging.getLogger(__name__)

# Shared, in-memory record of the most recent sync run. Updated by the
# scheduler via record_sync() and reported by the /health handler.
_STATE = {
    "last_sync": {
        "ran_at": None,
        "success": None,
        "returncode": None,
    }
}


def record_sync(success: bool, returncode: int, ran_at: str) -> None:
    """Record the outcome of the latest sync run for the health endpoint."""
    _STATE["last_sync"] = {
        "ran_at": ran_at,
        "success": success,
        "returncode": returncode,
    }


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 (name mandated by BaseHTTPRequestHandler)
        if self.path.rstrip("/") in ("", "/health"):
            payload = json.dumps({"status": "ok", **_STATE}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        else:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

    def log_message(self, format, *args):  # silence default stderr access log
        return


def start_health_server(port: int = 8080) -> ThreadingHTTPServer:
    """Start the health server in a daemon thread and return it.

    Pass ``port=0`` to bind an OS-assigned free port (useful in tests); read
    the actual port back from ``server.server_address[1]``.
    """
    server = ThreadingHTTPServer(("0.0.0.0", port), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Health endpoint listening on port {server.server_address[1]} at /health")
    return server
