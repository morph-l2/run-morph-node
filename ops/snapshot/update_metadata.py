#!/usr/bin/env python3
from __future__ import annotations
"""
Fetch snapshot metadata from the indexer API and update README.md via GitHub API.

Given BASE_HEIGHT and SNAPSHOT_NAME, this script:
  1. Queries the internal explorer-indexer API for l1_msg_start_height
     and derivation_start_height.
  2. Fetches README.md content from GitHub, applies the table update in memory.
  3. Creates a new branch, pushes the updated file, and opens a PR —
     all via GitHub REST API (no git or gh CLI required).

Environment variables:
  ENVIRONMENT         - mainnet | hoodi | holesky
  SNAPSHOT_NAME       - e.g. snapshot-20260225-1
  BASE_HEIGHT         - L2 geth block height
  GH_TOKEN            - GitHub personal access token (repo scope)
  GITHUB_REPOSITORY   - owner/repo, e.g. morphl2/run-morph-node
  README_PATH         - path to README.md inside the repo (default: README.md)
  L1_MSG_HEIGHT       - (optional) skip indexer API, use this value directly
  DERIV_HEIGHT        - (optional) skip indexer API, use this value directly
  DRY_RUN             - set to "1" to skip README update and PR creation

Usage:
  # Full run (on Self-hosted Runner, hits internal indexer API):
  ENVIRONMENT=mainnet SNAPSHOT_NAME=snapshot-20260225-1 BASE_HEIGHT=20169165 \\
    GH_TOKEN=ghp_xxx GITHUB_REPOSITORY=morphl2/run-morph-node \\
    python3 ops/snapshot/update_metadata.py

  # Local test with mock values — no git/gh CLI needed:
  ENVIRONMENT=mainnet SNAPSHOT_NAME=snapshot-test-1 BASE_HEIGHT=20169165 \\
    L1_MSG_HEIGHT=24280251 DERIV_HEIGHT=24294756 \\
    GH_TOKEN=ghp_xxx GITHUB_REPOSITORY=morphl2/run-morph-node \\
    python3 ops/snapshot/update_metadata.py

  # Dry run — only fetches/prints metadata, touches nothing:
  ENVIRONMENT=mainnet SNAPSHOT_NAME=snapshot-test-1 BASE_HEIGHT=20169165 \\
    L1_MSG_HEIGHT=24280251 DERIV_HEIGHT=24294756 DRY_RUN=1 \\
    python3 ops/snapshot/update_metadata.py
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.request

# ── Constants ─────────────────────────────────────────────────────────────────

INDEXER_BASE_URLS = {
    "mainnet": "https://explorer-indexer.morphl2.io",
    "hoodi":   "https://explorer-indexer-hoodi.morphl2.io",
    "holesky": "https://explorer-indexer-holesky.morphl2.io",
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _http_request(req: urllib.request.Request, url: str) -> dict:
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code} {e.reason} — URL: {url}\nResponse: {body}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error — URL: {url}\n{e.reason}") from None


def http_get(url: str, token: str = "") -> dict:
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; morph-snapshot/1.0)",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return _http_request(urllib.request.Request(url, headers=headers), url)


def http_get_or_none(url: str, token: str = "") -> dict | None:
    """Like http_get but returns None on 404 instead of raising."""
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code} {e.reason} — URL: {url}\nResponse: {body}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error — URL: {url}\n{e.reason}") from None


def http_post(url: str, payload: dict, token: str) -> dict:
    data    = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    return _http_request(urllib.request.Request(url, data=data, headers=headers, method="POST"), url)


def http_put(url: str, payload: dict, token: str) -> dict:
    data    = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    return _http_request(urllib.request.Request(url, data=data, headers=headers, method="PUT"), url)

# ── Indexer API ───────────────────────────────────────────────────────────────

def fetch_metadata(environment: str, base_height: str) -> tuple[str, str]:
    """Return (l1_msg_start_height, derivation_start_height) as strings."""
    # INDEXER_URL overrides the default public URL, useful for internal/intranet access.
    base_url = os.environ.get("EXPLORER_INDEXER_URL", INDEXER_BASE_URLS.get(environment, ""))
    if not base_url:
        raise RuntimeError(f"No indexer URL for environment {environment!r}. Set INDEXER_URL.")

    def get(path):
        url = f"{base_url.rstrip('/')}{path}"
        print(f"  GET {url}")
        return http_get(url)

    l1_data    = get(f"/v1/batch/l1_msg_start_height/{base_height}")
    deriv_data = get(f"/v1/batch/derivation_start_height/{base_height}")

    # API may return a plain number or a dict like {"l1_msg_start_height": N}
    if isinstance(l1_data, (int, float)):
        l1_msg_height = str(int(l1_data))
    elif isinstance(l1_data, dict) and "l1_msg_start_height" in l1_data:
        l1_msg_height = str(l1_data["l1_msg_start_height"])
    else:
        raise RuntimeError(f"Unexpected indexer response for l1_msg_start_height: {l1_data}")

    if isinstance(deriv_data, (int, float)):
        deriv_height = str(int(deriv_data))
    elif isinstance(deriv_data, dict) and "derivation_start_height" in deriv_data:
        deriv_height = str(deriv_data["derivation_start_height"])
    else:
        raise RuntimeError(f"Unexpected indexer response for derivation_start_height: {deriv_data}")

    return l1_msg_height, deriv_height

# ── GitHub API ────────────────────────────────────────────────────────────────

GITHUB_API = "https://api.github.com"


def gh_get_file(repo: str, path: str, token: str, ref: str = "main") -> tuple[str, str]:
    """Fetch file content. Returns (decoded_content, blob_sha)."""
    url  = f"{GITHUB_API}/repos/{repo}/contents/{path}?ref={ref}"
    data = http_get(url, token)
    content = base64.b64decode(data["content"]).decode("utf-8")
    return content, data["sha"]


def gh_get_main_sha(repo: str, token: str) -> str:
    """Return the current commit SHA of the main branch."""
    url  = f"{GITHUB_API}/repos/{repo}/git/ref/heads/main"
    data = http_get(url, token)
    return data["object"]["sha"]


def gh_branch_exists(repo: str, branch: str, token: str) -> bool:
    url = f"{GITHUB_API}/repos/{repo}/git/ref/heads/{branch}"
    return http_get_or_none(url, token) is not None


def resolve_snapshot_name(repo: str, environment: str,
                          snapshot_name: str, token: str) -> str:
    """Verify that the snapshot branch does not already exist on GitHub.

    Each date should have exactly one snapshot. If the branch for snapshot_name
    already exists it means today's snapshot was already created — raise an error
    instead of silently creating a -2 duplicate.
    """
    branch = f"snapshot/{environment}-{snapshot_name}"
    if gh_branch_exists(repo, branch, token):
        raise RuntimeError(
            f"Branch '{branch}' already exists on GitHub.\n"
            f"  Today's snapshot ({snapshot_name}) has already been created.\n"
            f"  If you need to re-run, delete the branch first or use a different SNAPSHOT_PREFIX."
        )
    return snapshot_name


def gh_create_branch(repo: str, branch: str, sha: str, token: str) -> None:
    """Create branch. snapshot_name must already be resolved via resolve_snapshot_name."""
    url = f"{GITHUB_API}/repos/{repo}/git/refs"
    http_post(url, {"ref": f"refs/heads/{branch}", "sha": sha}, token)
    print(f"  Created branch: {branch}")


def gh_update_file(repo: str, path: str, content: str,
                   blob_sha: str, branch: str, message: str, token: str) -> None:
    url = f"{GITHUB_API}/repos/{repo}/contents/{path}"
    http_put(url, {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode(),
        "sha":     blob_sha,
        "branch":  branch,
    }, token)
    print(f"  Pushed {path} to branch: {branch}")


def gh_create_pr(repo: str, branch: str, title: str, body: str, token: str) -> str:
    url  = f"{GITHUB_API}/repos/{repo}/pulls"
    data = http_post(url, {
        "title": title,
        "body":  body,
        "head":  branch,
        "base":  "main",
    }, token)
    return data["html_url"]

# ── README update (in-memory) ─────────────────────────────────────────────────

def build_new_row(environment: str, snapshot_name: str,
                  deriv_height: str, l1_msg_height: str, base_height: str) -> str:
    cdn_base = "https://snapshot.morphl2.io"
    url = f"{cdn_base}/{environment}/{snapshot_name}.tar.gz"
    return f"| [{snapshot_name}]({url}) | {deriv_height} | {l1_msg_height} | {base_height} |"


def apply_readme_update(content: str, environment: str, snapshot_name: str,
                        deriv_height: str, l1_msg_height: str, base_height: str) -> str:
    """Import insert_row_content from update_readme.py and apply it."""
    from update_readme import insert_row_content, SECTION_MARKERS  # noqa: E402

    section_marker = SECTION_MARKERS[environment]
    new_row        = build_new_row(environment, snapshot_name, deriv_height, l1_msg_height, base_height)
    return insert_row_content(content, section_marker, new_row)

# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    from update_readme import write_metric  # noqa: E402

    dry_run = os.environ.get("DRY_RUN", "0") == "1"

    # Validate required env vars
    required = ["ENVIRONMENT", "SNAPSHOT_NAME", "BASE_HEIGHT"]
    if not dry_run:
        required += ["GH_TOKEN", "GITHUB_REPOSITORY"]

    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        print(f"ERROR: Missing required env vars: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    environment   = os.environ["ENVIRONMENT"]
    snapshot_name = os.environ["SNAPSHOT_NAME"]
    base_height   = os.environ["BASE_HEIGHT"]
    token         = os.environ.get("GH_TOKEN", "")
    repo          = os.environ.get("GITHUB_REPOSITORY", "")
    readme_path   = os.environ.get("README_PATH", "README.md")

    if environment not in INDEXER_BASE_URLS:
        print(f"ERROR: Unknown environment: {environment!r}. Must be: {' | '.join(INDEXER_BASE_URLS)}",
              file=sys.stderr)
        sys.exit(1)

    try:
        # ── Step 1: metadata ──────────────────────────────────────────────────
        l1_msg_height = os.environ.get("L1_MSG_HEIGHT", "")
        deriv_height  = os.environ.get("DERIV_HEIGHT", "")

        if l1_msg_height and deriv_height:
            print(f"\n[1/3] Using provided metadata (API call skipped):")
        else:
            print(f"\n[1/3] Fetching metadata from indexer (base_height={base_height}) ...")
            l1_msg_height, deriv_height = fetch_metadata(environment, base_height)

        print(f"      l1_msg_start_height      = {l1_msg_height}")
        print(f"      derivation_start_height  = {deriv_height}")

        if dry_run:
            print("\n[DRY RUN] Skipping README update and PR creation.")
            print(f"          Would insert: env={environment} snapshot={snapshot_name}")
            print(f"          base={base_height} l1_msg={l1_msg_height} deriv={deriv_height}")
            return

        # ── Step 2: update README in memory, push via GitHub API ─────────────
        print(f"\n[2/3] Updating README via GitHub API ...")
        current_content, blob_sha = gh_get_file(repo, readme_path, token)
        updated_content           = apply_readme_update(
            current_content, environment, snapshot_name, deriv_height, l1_msg_height, base_height
        )

        branch     = f"snapshot/{environment}-{snapshot_name}"
        commit_msg = f"snapshot: add {snapshot_name} ({environment})"
        main_sha   = gh_get_main_sha(repo, token)

        gh_create_branch(repo, branch, main_sha, token)
        gh_update_file(repo, readme_path, updated_content, blob_sha, branch, commit_msg, token)

        # ── Step 3: open PR ───────────────────────────────────────────────────
        print(f"\n[3/3] Creating PR ...")
        pr_body = (
            f"Auto-generated by snapshot workflow.\n\n"
            f"- Environment: `{environment}`\n"
            f"- Snapshot: `{snapshot_name}`\n"
            f"- L2 Base Height: `{base_height}`\n"
            f"- L1 Msg Start Height: `{l1_msg_height}`\n"
            f"- Derivation Start Height: `{deriv_height}`"
        )
        pr_url = gh_create_pr(repo, branch, commit_msg, pr_body, token)

        print(f"\n✅ Done. PR opened: {pr_url}")
        write_metric(1, environment, snapshot_name)

    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        write_metric(0, environment, snapshot_name)
        sys.exit(1)


if __name__ == "__main__":
    main()
