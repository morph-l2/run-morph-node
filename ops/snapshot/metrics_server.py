#!/usr/bin/env python3
from __future__ import annotations
"""
Lightweight Prometheus metrics HTTP server for morph snapshot automation.

Reads a .prom file written by the snapshot scripts (snapshot_make.py /
update_metadata.py / update_readme.py) and serves it on :6060/metrics, plus
a set of live metrics collected on every scrape:

  morph_snapshot_readme_update_status      - from the .prom file (1 ok / 0 fail)
  morph_snapshot_readme_update_timestamp_seconds - from the .prom file
  morph_snapshot_exec_block_height                  - eth_blockNumber on the EL RPC
  morph_snapshot_client_version{client="geth|reth|node",version="..."} - binary versions

Intended to run as a persistent process (e.g. managed by pm2).

Environment variables:
  METRICS_FILE  - path to the .prom file  (default: /tmp/morph_snapshot_metrics.prom)
  METRICS_PORT  - port to listen on        (default: 6060)
  ENVIRONMENT   - label applied to live metrics (default: unknown)
  GETH_RPC      - execution-layer RPC (geth/reth share it) (default: http://127.0.0.1:8545)
  MORPH_HOME    - node home dir; binaries default to $MORPH_HOME/bin (default: /data/morph-mainnet)
  MORPH_BIN_DIR - override the binary dir directly (default: $MORPH_HOME/bin)
  GETH_BIN / RETH_BIN / NODE_BIN - override individual binary paths
"""

import http.server
import json
import os
import re
import socket
import subprocess
import time
import urllib.request

METRICS_FILE = os.environ.get("METRICS_FILE", "/tmp/morph_snapshot_metrics.prom")
PORT = int(os.environ.get("METRICS_PORT", "6060"))

ENVIRONMENT = os.environ.get("ENVIRONMENT", "unknown")

# Execution-layer RPC (geth and reth both expose eth_blockNumber on the same port).
GETH_RPC = os.environ.get("GETH_RPC") or "http://127.0.0.1:8545"

# Client binaries. Paths default to $MORPH_HOME/bin (matching snapshot_make.py's
# use of MORPH_HOME) but can be overridden per environment (see CLAUDE.md: never
# hardcode paths).
MORPH_HOME = os.environ.get("MORPH_HOME") or "/data/morph-mainnet"
BIN_DIR    = os.environ.get("MORPH_BIN_DIR") or os.path.join(MORPH_HOME, "bin")
GETH_BIN   = os.environ.get("GETH_BIN") or os.path.join(BIN_DIR, "geth")
RETH_BIN   = os.environ.get("RETH_BIN") or os.path.join(BIN_DIR, "morph-reth")
NODE_BIN   = os.environ.get("NODE_BIN") or os.path.join(BIN_DIR, "morphnode")

# Each entry: (metric-label value, argv). argv is the version command to run.
VERSION_TARGETS = {
    "geth": [GETH_BIN, "version"],
    "reth": [RETH_BIN, "--version"],
    "node": [NODE_BIN, "version"],
}

# Matches a semver-ish token like 1.2.3, v1.2.3, 0.1.0-rc1, 1.14.11-stable-abc123.
_VERSION_RE = re.compile(r"\bv?(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?)\b")


def _empty_metrics() -> str:
    """Fallback served when METRICS_FILE cannot be read (missing/permissions).

    Emits status=0 with a distinct snapshot="unavailable" label so Prometheus
    scrapes a clear failure signal instead of getting an empty reply.
    """
    environment = os.environ.get("ENVIRONMENT", "unknown")
    ts = int(time.time())
    return (
        "# HELP morph_snapshot_readme_update_status 1 if last README update succeeded, 0 if failed\n"
        "# TYPE morph_snapshot_readme_update_status gauge\n"
        f'morph_snapshot_readme_update_status{{environment="{environment}",snapshot="unavailable"}} 0\n'
        "# HELP morph_snapshot_readme_update_timestamp_seconds Unix timestamp of last run\n"
        "# TYPE morph_snapshot_readme_update_timestamp_seconds gauge\n"
        f'morph_snapshot_readme_update_timestamp_seconds{{environment="{environment}",snapshot="unavailable"}} {ts}\n'
    )


def _default_metrics() -> str:
    """Default metrics written on first startup — status=1 to avoid false alarms."""
    environment = os.environ.get("ENVIRONMENT", "unknown")
    ts = int(time.time())
    return (
        "# HELP morph_snapshot_readme_update_status 1 if last README update succeeded, 0 if failed\n"
        "# TYPE morph_snapshot_readme_update_status gauge\n"
        f'morph_snapshot_readme_update_status{{environment="{environment}",snapshot="pending"}} 1\n'
        "# HELP morph_snapshot_readme_update_timestamp_seconds Unix timestamp of last run\n"
        "# TYPE morph_snapshot_readme_update_timestamp_seconds gauge\n"
        f'morph_snapshot_readme_update_timestamp_seconds{{environment="{environment}",snapshot="pending"}} {ts}\n'
    )


def _init_metrics_file() -> None:
    """Write default metrics if file does not exist yet."""
    if not os.path.exists(METRICS_FILE):
        try:
            with open(METRICS_FILE, "w") as f:
                f.write(_default_metrics())
            print(f"Initialized default metrics: {METRICS_FILE}")
        except OSError as e:
            print(f"WARNING: could not initialize metrics file: {e}")


# ── Live metrics (collected on each scrape) ─────────────────────────────────────

def _escape_label(value: str) -> str:
    """Escape a string for use as a Prometheus label value."""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def get_exec_block_height() -> int | None:
    """Query eth_blockNumber on the execution-layer RPC. Returns None on failure."""
    payload = json.dumps({
        "jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1
    }).encode()
    try:
        req = urllib.request.Request(
            GETH_RPC, data=payload, headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            result = json.loads(resp.read())["result"]
            if result:
                return int(result, 16)
    except Exception:
        pass
    return None


def get_client_version(argv: list) -> str | None:
    """Run a client's version command and extract a version string.

    Returns the first semver-ish token found, else the first non-empty output
    line (trimmed), else None if the command fails or the binary is missing.
    """
    try:
        out = subprocess.run(
            argv, capture_output=True, text=True, timeout=5,
        ).stdout
    except Exception:
        return None
    if not out:
        return None
    m = _VERSION_RE.search(out)
    if m:
        return m.group(1)
    for line in out.splitlines():
        line = line.strip()
        if line:
            return line[:64]
    return None


def collect_live_metrics() -> str:
    """Build the block-height and client-version metrics for the current scrape."""
    lines = []

    height = get_exec_block_height()
    lines.append(
        "# HELP morph_snapshot_exec_block_height Latest execution-layer block height (eth_blockNumber)"
    )
    lines.append("# TYPE morph_snapshot_exec_block_height gauge")
    if height is not None:
        lines.append(
            f'morph_snapshot_exec_block_height{{environment="{ENVIRONMENT}"}} {height}'
        )
    # On failure we emit no sample so the metric goes stale rather than reporting 0.

    lines.append(
        "# HELP morph_snapshot_client_version Client version reported by the binary (value in 'version' label, always 1)"
    )
    lines.append("# TYPE morph_snapshot_client_version gauge")
    for client, argv in VERSION_TARGETS.items():
        version = get_client_version(argv)
        if version is None:
            continue
        labels = (
            f'environment="{ENVIRONMENT}",client="{client}",'
            f'version="{_escape_label(version)}"'
        )
        lines.append(f"morph_snapshot_client_version{{{labels}}} 1")

    return "\n".join(lines) + "\n"


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
            content = _empty_metrics()
            self.send_response(200)

        # Append live metrics (block height + client versions) collected per scrape.
        if not content.endswith("\n"):
            content += "\n"
        content += collect_live_metrics()

        body = content.encode("utf-8")
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        # Suppress per-request access logs to keep output clean
        pass


if __name__ == "__main__":
    _init_metrics_file()
    server = http.server.HTTPServer(("0.0.0.0", PORT), MetricsHandler)
    host = socket.gethostname()
    print(f"morph-snapshot metrics server listening on http://{host}:{PORT}/metrics")
    print(f"Reading metrics from: {METRICS_FILE}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()

