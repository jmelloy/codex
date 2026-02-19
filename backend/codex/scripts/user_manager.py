#!/usr/bin/env python3
"""
User management utilities for Codex.

Provides functions and a CLI for registering users, obtaining tokens,
and querying user info via the HTTP API. The server must be running.

Usage:
    python -m codex.scripts.user_manager register <username> <email> <password>
    python -m codex.scripts.user_manager token <username> <password>
    python -m codex.scripts.user_manager me --token <token>
"""

import json
import os
import sys

import httpx


def get_base_url() -> str:
    """Return the API base URL from env or default."""
    return os.environ.get("CODEX_API_URL", "http://localhost:8000")


def register_user(base_url: str, username: str, email: str, password: str) -> dict:
    """Register a new user. Returns the JSON response dict."""
    r = httpx.post(
        f"{base_url}/api/v1/users/register",
        json={"username": username, "email": email, "password": password},
    )
    r.raise_for_status()
    return r.json()


def get_token(base_url: str, username: str, password: str) -> str:
    """Obtain a bearer token. Returns the token string."""
    r = httpx.post(
        f"{base_url}/api/v1/users/token",
        data={"username": username, "password": password},
    )
    r.raise_for_status()
    return r.json()["access_token"]


def get_me(base_url: str, token: str) -> dict:
    """Get current user info. Returns the JSON response dict."""
    r = httpx.get(
        f"{base_url}/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()
    return r.json()


def _die(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="user_manager",
        description="Codex user management CLI",
    )
    sub = parser.add_subparsers(dest="command")

    # register
    p_reg = sub.add_parser("register", help="Register a new user")
    p_reg.add_argument("username")
    p_reg.add_argument("email")
    p_reg.add_argument("password")

    # token
    p_tok = sub.add_parser("token", help="Get a bearer token")
    p_tok.add_argument("username")
    p_tok.add_argument("password")

    # me
    p_me = sub.add_parser("me", help="Get current user info")
    p_me.add_argument("--token", required=True, help="Bearer token")

    args = parser.parse_args()
    base_url = get_base_url()

    if args.command == "register":
        try:
            result = register_user(base_url, args.username, args.email, args.password)
            print(json.dumps(result, indent=2))
        except httpx.HTTPStatusError as e:
            _die(f"Registration failed ({e.response.status_code}): {e.response.text}")

    elif args.command == "token":
        try:
            token = get_token(base_url, args.username, args.password)
            # Print ONLY the token string so callers can capture it
            print(token)
        except httpx.HTTPStatusError as e:
            _die(f"Auth failed ({e.response.status_code}): {e.response.text}")

    elif args.command == "me":
        try:
            result = get_me(base_url, args.token)
            print(json.dumps(result, indent=2))
        except httpx.HTTPStatusError as e:
            _die(f"Request failed ({e.response.status_code}): {e.response.text}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
