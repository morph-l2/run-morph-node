#!/usr/bin/env bash
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 <config_file_path>"
  exit 1
fi

config="$1"
if [ ! -f "$config" ]; then
  echo "Error: file not found: $config" >&2
  exit 1
fi

tmp=$(mktemp -p "$(dirname "$config")" .config.XXXXXX)
trap 'rm -f "$tmp"' EXIT

sed -e '/^[[:space:]]*#/!s/^[[:space:]]*timeout_commit[[:space:]]*=.*/timeout_commit = "300ms"/' \
    -e '/^[[:space:]]*#/!s/^[[:space:]]*peer_gossip_sleep_duration[[:space:]]*=.*/peer_gossip_sleep_duration = "10ms"/' \
    -e '/^[[:space:]]*#/!s/^[[:space:]]*flush_throttle_timeout[[:space:]]*=.*/flush_throttle_timeout = "10ms"/' \
    -e '/^[[:space:]]*#/!s/^[[:space:]]*send_rate[[:space:]]*=.*/send_rate = 52428800/' \
    -e '/^[[:space:]]*#/!s/^[[:space:]]*recv_rate[[:space:]]*=.*/recv_rate = 102428800/' \
    "$config" > "$tmp"

mv "$tmp" "$config"

grep -qE '^[[:space:]]*timeout_commit[[:space:]]*=' "$config" || echo 'timeout_commit = "300ms"' >> "$config"
grep -qE '^[[:space:]]*peer_gossip_sleep_duration[[:space:]]*=' "$config" || echo 'peer_gossip_sleep_duration = "10ms"' >> "$config"
grep -qE '^[[:space:]]*flush_throttle_timeout[[:space:]]*=' "$config" || echo 'flush_throttle_timeout = "10ms"' >> "$config"
grep -qE '^[[:space:]]*send_rate[[:space:]]*=' "$config" || echo 'send_rate = 52428800' >> "$config"
grep -qE '^[[:space:]]*recv_rate[[:space:]]*=' "$config" || echo 'recv_rate = 102428800' >> "$config"

echo "Successfully updated: $config"