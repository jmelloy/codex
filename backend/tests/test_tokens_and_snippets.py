"""Tests for personal access tokens and snippet posting."""

import time

import pytest
from fastapi.testclient import TestClient

from codex.main import app


@pytest.fixture
def user_and_token(test_client):
    """Register a user and return (headers_dict, username, jwt_token)."""
    username = f"pat_user_{int(time.time() * 1000)}"
    email = f"{username}@example.com"
    password = "testpass123"

    reg = test_client.post(
        "/api/v1/users/register",
        json={"username": username, "email": email, "password": password},
    )
    assert reg.status_code == 201

    login = test_client.post(
        "/api/v1/users/token",
        data={"username": username, "password": password},
    )
    assert login.status_code == 200
    jwt_token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {jwt_token}"}
    return headers, username, jwt_token


# ── Personal Access Token Tests ──────────────────────────────────────


class TestPersonalAccessTokens:
    def test_create_token(self, test_client, user_and_token):
        headers, username, _ = user_and_token
        resp = test_client.post(
            "/api/v1/tokens/",
            json={"name": "test-token"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "test-token"
        assert data["token"].startswith("cdx_")
        assert data["token_prefix"] == data["token"][:12]
        assert data["id"] is not None

    def test_list_tokens(self, test_client, user_and_token):
        headers, _, _ = user_and_token

        # Create two tokens
        test_client.post("/api/v1/tokens/", json={"name": "tok-1"}, headers=headers)
        test_client.post("/api/v1/tokens/", json={"name": "tok-2"}, headers=headers)

        resp = test_client.get("/api/v1/tokens/", headers=headers)
        assert resp.status_code == 200
        tokens = resp.json()
        names = [t["name"] for t in tokens]
        assert "tok-1" in names
        assert "tok-2" in names
        # Plain token should NOT appear in list
        for t in tokens:
            assert "token" not in t or t.get("token") is None

    def test_revoke_token(self, test_client, user_and_token):
        headers, _, _ = user_and_token

        create_resp = test_client.post(
            "/api/v1/tokens/", json={"name": "to-revoke"}, headers=headers
        )
        token_id = create_resp.json()["id"]

        # Revoke
        del_resp = test_client.delete(f"/api/v1/tokens/{token_id}", headers=headers)
        assert del_resp.status_code == 204

        # Verify it shows as inactive
        list_resp = test_client.get("/api/v1/tokens/", headers=headers)
        revoked = [t for t in list_resp.json() if t["id"] == token_id]
        assert len(revoked) == 1
        assert revoked[0]["is_active"] is False

    def test_revoke_nonexistent_token(self, test_client, user_and_token):
        headers, _, _ = user_and_token
        resp = test_client.delete("/api/v1/tokens/99999", headers=headers)
        assert resp.status_code == 404

    def test_authenticate_with_pat(self, test_client, user_and_token):
        headers, username, _ = user_and_token

        # Create a PAT
        create_resp = test_client.post(
            "/api/v1/tokens/", json={"name": "auth-test"}, headers=headers
        )
        pat = create_resp.json()["token"]

        # Use PAT to access /users/me
        pat_headers = {"Authorization": f"Bearer {pat}"}
        me_resp = test_client.get("/api/v1/users/me", headers=pat_headers)
        assert me_resp.status_code == 200
        assert me_resp.json()["username"] == username

    def test_revoked_pat_rejected(self, test_client, user_and_token):
        headers, _, _ = user_and_token

        # Create and revoke a PAT
        create_resp = test_client.post(
            "/api/v1/tokens/", json={"name": "revoke-test"}, headers=headers
        )
        pat = create_resp.json()["token"]
        token_id = create_resp.json()["id"]

        test_client.delete(f"/api/v1/tokens/{token_id}", headers=headers)

        # Attempt to use revoked PAT
        pat_headers = {"Authorization": f"Bearer {pat}"}
        me_resp = test_client.get("/api/v1/users/me", headers=pat_headers)
        assert me_resp.status_code == 401

    def test_invalid_pat_rejected(self, test_client):
        headers = {"Authorization": "Bearer cdx_invalid_token_value"}
        resp = test_client.get("/api/v1/users/me", headers=headers)
        assert resp.status_code == 401

    def test_create_token_with_scopes(self, test_client, user_and_token):
        headers, _, _ = user_and_token
        resp = test_client.post(
            "/api/v1/tokens/",
            json={"name": "scoped-token", "scopes": "snippets:write"},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["scopes"] == "snippets:write"


# ── Snippet Posting Tests ────────────────────────────────────────────


class TestSnippetPosting:
    @pytest.fixture
    def workspace_notebook_and_pat(self, test_client, user_and_token):
        """Create a workspace, notebook, and PAT for snippet tests."""
        headers, username, _ = user_and_token

        # Get default workspace (created during registration)
        ws_resp = test_client.get("/api/v1/workspaces/", headers=headers)
        assert ws_resp.status_code == 200
        workspaces = ws_resp.json()
        assert len(workspaces) > 0
        workspace = workspaces[0]

        # Create a notebook
        nb_resp = test_client.post(
            f"/api/v1/workspaces/{workspace['slug']}/notebooks/",
            json={"name": "Snippet Notebook"},
            headers=headers,
        )
        assert nb_resp.status_code == 200
        notebook = nb_resp.json()

        # Create a PAT
        pat_resp = test_client.post(
            "/api/v1/tokens/", json={"name": "snippet-pat"}, headers=headers
        )
        pat = pat_resp.json()["token"]

        return workspace, notebook, pat, headers

    def test_post_snippet_with_jwt(self, test_client, workspace_notebook_and_pat):
        workspace, notebook, _, headers = workspace_notebook_and_pat

        resp = test_client.post(
            "/api/v1/snippets/",
            json={
                "workspace": workspace["slug"],
                "notebook": notebook["slug"],
                "content": "print('hello world')",
                "title": "Hello World",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["message"] == "Snippet created successfully"
        assert "hello-world" in data["filename"].lower()
        assert data["id"] is not None

    def test_post_snippet_with_pat(self, test_client, workspace_notebook_and_pat):
        workspace, notebook, pat, _ = workspace_notebook_and_pat
        pat_headers = {"Authorization": f"Bearer {pat}"}

        resp = test_client.post(
            "/api/v1/snippets/",
            json={
                "workspace": workspace["slug"],
                "notebook": notebook["slug"],
                "content": "# Note from pre-commit hook\nCode was committed.",
                "title": "Pre-commit Note",
                "tags": ["automation", "git"],
                "file_type": "log",
            },
            headers=pat_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Pre-commit Note"

    def test_post_snippet_without_title(self, test_client, workspace_notebook_and_pat):
        workspace, notebook, pat, _ = workspace_notebook_and_pat
        pat_headers = {"Authorization": f"Bearer {pat}"}

        resp = test_client.post(
            "/api/v1/snippets/",
            json={
                "workspace": workspace["slug"],
                "notebook": notebook["slug"],
                "content": "Quick note without a title",
            },
            headers=pat_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "snippet" in data["filename"].lower()

    def test_post_snippet_with_custom_filename(self, test_client, workspace_notebook_and_pat):
        workspace, notebook, _, headers = workspace_notebook_and_pat

        resp = test_client.post(
            "/api/v1/snippets/",
            json={
                "workspace": workspace["slug"],
                "notebook": notebook["slug"],
                "content": "Custom file",
                "filename": "my-custom-file.md",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["filename"] == "my-custom-file.md"

    def test_post_snippet_with_folder(self, test_client, workspace_notebook_and_pat):
        workspace, notebook, _, headers = workspace_notebook_and_pat

        resp = test_client.post(
            "/api/v1/snippets/",
            json={
                "workspace": workspace["slug"],
                "notebook": notebook["slug"],
                "content": "Filed snippet",
                "title": "Filed",
                "folder": "logs",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["path"].startswith("logs/")

    def test_post_snippet_duplicate_name_gets_suffix(self, test_client, workspace_notebook_and_pat):
        workspace, notebook, _, headers = workspace_notebook_and_pat

        payload = {
            "workspace": workspace["slug"],
            "notebook": notebook["slug"],
            "content": "Duplicate test",
            "filename": "dup-test.md",
        }

        resp1 = test_client.post("/api/v1/snippets/", json=payload, headers=headers)
        assert resp1.status_code == 201

        resp2 = test_client.post("/api/v1/snippets/", json=payload, headers=headers)
        assert resp2.status_code == 201
        # Second file should have a different path
        assert resp2.json()["path"] != resp1.json()["path"]

    def test_post_snippet_invalid_workspace(self, test_client, workspace_notebook_and_pat):
        _, notebook, _, headers = workspace_notebook_and_pat

        resp = test_client.post(
            "/api/v1/snippets/",
            json={
                "workspace": "nonexistent-workspace",
                "notebook": notebook["slug"],
                "content": "Should fail",
            },
            headers=headers,
        )
        assert resp.status_code == 404

    def test_post_snippet_invalid_notebook(self, test_client, workspace_notebook_and_pat):
        workspace, _, _, headers = workspace_notebook_and_pat

        resp = test_client.post(
            "/api/v1/snippets/",
            json={
                "workspace": workspace["slug"],
                "notebook": "nonexistent-notebook",
                "content": "Should fail",
            },
            headers=headers,
        )
        assert resp.status_code == 404

    def test_post_snippet_requires_auth(self, test_client):
        resp = test_client.post(
            "/api/v1/snippets/",
            json={
                "workspace": "any",
                "notebook": "any",
                "content": "No auth",
            },
        )
        assert resp.status_code == 401

    def test_post_snippet_with_properties(self, test_client, workspace_notebook_and_pat):
        workspace, notebook, _, headers = workspace_notebook_and_pat

        resp = test_client.post(
            "/api/v1/snippets/",
            json={
                "workspace": workspace["slug"],
                "notebook": notebook["slug"],
                "content": "Snippet with extra metadata",
                "title": "Metadata Test",
                "properties": {"source": "pre-commit", "repo": "codex"},
            },
            headers=headers,
        )
        assert resp.status_code == 201
