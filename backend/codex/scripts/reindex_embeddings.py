"""Drop and recreate page_embeddings tables, then re-vectorize all notebooks.

Usage:
    python -m codex.scripts.reindex_embeddings [--api-url URL]

Connects to the running Codex API to trigger re-vectorization after the
embedding model or dimensions change.
"""

import argparse
import os
import sys

import httpx


def main():
    parser = argparse.ArgumentParser(description="Re-index all page embeddings")
    parser.add_argument("--api-url", default=os.getenv("CODEX_API_URL", "http://localhost:8765"))
    parser.add_argument("--username", default="demo")
    parser.add_argument("--password", default="demo123456")
    parser.add_argument("--no-reset", action="store_true", help="Skip dropping/recreating the embeddings table")
    args = parser.parse_args()

    base = args.api_url.rstrip("/")
    client = httpx.Client(base_url=base, timeout=120.0)

    # Authenticate
    resp = client.post("/api/v1/users/login", json={"username": args.username, "password": args.password})
    if resp.status_code != 200:
        print(f"Login failed: {resp.status_code} {resp.text}")
        sys.exit(1)

    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    print(f"Authenticated as {args.username}")

    # List workspaces
    workspaces = client.get("/api/v1/workspaces/").json()
    if not workspaces:
        print("No workspaces found")
        sys.exit(0)

    total = 0
    for ws in workspaces:
        ws_slug = ws["slug"]
        notebooks = client.get(f"/api/v1/workspaces/{ws_slug}/notebooks/").json()
        for nb in notebooks:
            nb_slug = nb["slug"]
            reset = not args.no_reset
            print(f"Vectorizing {ws_slug}/{nb_slug} (reset={reset})...", end=" ", flush=True)
            resp = client.post(f"/api/v1/workspaces/{ws_slug}/notebooks/{nb_slug}/vectorize", params={"reset": reset})
            if resp.status_code == 200:
                count = resp.json().get("pages_vectorized", 0)
                total += count
                print(f"{count} pages")
            else:
                print(f"FAILED ({resp.status_code})")

    print(f"\nDone. Total pages vectorized: {total}")


if __name__ == "__main__":
    main()
