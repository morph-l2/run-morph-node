#!/usr/bin/env python3
"""
Lightweight Prometheus metrics HTTP server for morph snapshot automation.

Reads a .prom file written by update_readme.py and serves it on :6060/metrics.
Intended to run as a persistent process (e.g. managed by pm2).

Environment variables:
  METRICS_FILE  - path to the .prom file  (default: /tmp/morph_snapshot_metrics.prom)
  METRICS_PORT  - port to listen on        (default: 6060)
"""

import http.server
import os
import socket

METRICS_FILE = os.environ.get("METRICS_FILE", "/tmp/morph_snapshot_metrics.prom")
PORT = int(os.environ.get("METRICS_PORT", "6060"))

EMPTY_METRICS = (
    "# HELP morph_snapshot_readme_update_status 1 if last README update succeeded, 0 if failed\n"
    "# TYPE morph_snapshot_readme_update_status gauge\n"
    "# (no data yet — update_readme.sh has not run)\n"
)


class MetricsHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return

        try:
            with open(METRICS_FILE, "r") as f:
                content = f.read()
            self.send_response(200)
        except OSError:
            content = EMPTY_METRICS
            self.send_response(200)

        body = content.encode("utf-8")
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        # Suppress per-request access logs to keep output clean
        pass


if __name__ == "__main__":
    server = http.server.HTTPServer(("0.0.0.0", PORT), MetricsHandler)
    host = socket.gethostname()
    print(f"morph-snapshot metrics server listening on http://{host}:{PORT}/metrics")
    print(f"Reading metrics from: {METRICS_FILE}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()

