#!/usr/bin/env python3
"""
Dead-simple Codex API caller for agents and bash scripts.

Stdout: clean JSON only (pipeable to jq).
Stderr: auth/error messages.
Exit 0 on 2xx, exit 1 otherwise.

Usage:
    python -m codex.scripts.api_tester --user demo --password demo123456 GET /api/v1/workspaces/
    python -m codex.scripts.api_tester --token $TOKEN POST /api/v1/workspaces/ '{"name":"New WS"}'
    python -m codex.scripts.api_tester --token $TOKEN DELETE /api/v1/workspaces/1/notebooks/1/files/3
"""

import json
import sys

import httpx

from codex.scripts.user_manager import get_base_url, get_token


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="api_tester",
        description="Minimal Codex API caller",
    )
    auth = parser.add_mutually_exclusive_group(required=True)
    auth.add_argument("--token", help="Bearer token")
    auth.add_argument("--user", help="Username (requires --password)")
    parser.add_argument("--password", help="Password (used with --user)")
    parser.add_argument("method", help="HTTP method (GET, POST, PUT, PATCH, DELETE)")
    parser.add_argument("path", help="API path, e.g. /api/v1/workspaces/")
    parser.add_argument("body", nargs="?", default=None, help="JSON body (optional)")

    args = parser.parse_args()
    base_url = get_base_url()

    # Resolve token
    token = args.token
    if args.user:
        if not args.password:
            print("--password is required with --user", file=sys.stderr)
            sys.exit(1)
        print(f"Authenticating as {args.user}...", file=sys.stderr)
        try:
            token = get_token(base_url, args.user, args.password)
        except httpx.HTTPStatusError as e:
            print(f"Auth failed ({e.response.status_code}): {e.response.text}", file=sys.stderr)
            sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}
    url = f"{base_url}{args.path}"
    method = args.method.upper()

    kwargs: dict = {"headers": headers}
    if args.body:
        kwargs["json"] = json.loads(args.body)

    r = httpx.request(method, url, **kwargs)

    # Output response body
    try:
        print(json.dumps(r.json(), indent=2))
    except Exception:
        print(r.text)

    if not r.is_success:
        print(f"HTTP {r.status_code}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
