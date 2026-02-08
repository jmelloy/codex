"""Integration tests replacing tests/integration/test_docker_integration.sh.

These tests exercise the full end-to-end API flow: health checks, user
registration and authentication, workspace CRUD, notebook CRUD, file
operations, search, task queue, query API, and CORS headers.

Unlike the shell-script version that hit a live Docker deployment with curl,
these tests use FastAPI's TestClient so they run in-process and require no
external services.
"""

import time

from fastapi.testclient import TestClient

from codex.main import app


# ---------------------------------------------------------------------------
# Helpers – each test gets a fresh client to avoid cookie bleed-through
# ---------------------------------------------------------------------------


def _fresh_client() -> TestClient:
    return TestClient(app)


def _register_and_login(client: TestClient) -> tuple[dict, str]:
    """Register a unique user and return (auth_headers, username)."""
    ts = int(time.time() * 1000)
    username = f"integration_{ts}"
    password = "testpass123"
    email = f"{username}@example.com"

    reg = client.post(
        "/api/v1/users/register",
        json={"username": username, "email": email, "password": password},
    )
    assert reg.status_code == 201, f"Registration failed: {reg.status_code} {reg.text}"
    assert reg.json()["username"] == username

    login = client.post(
        "/api/v1/users/token",
        data={"username": username, "password": password},
    )
    assert login.status_code == 200, f"Login failed: {login.status_code} {login.text}"
    token = login.json()["access_token"]
    assert token, "Token is empty"
    assert login.json()["token_type"] == "bearer"

    headers = {"Authorization": f"Bearer {token}"}
    return headers, username


# ---------------------------------------------------------------------------
# Backend health
# ---------------------------------------------------------------------------


class TestBackendHealth:
    """Corresponds to the 'Backend Health Tests' section of the shell script."""

    def test_health_endpoint(self):
        client = _fresh_client()
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_root_endpoint(self):
        client = _fresh_client()
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Codex API"

    def test_docs_available(self):
        client = _fresh_client()
        resp = client.get("/docs")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# User Registration & Authentication
# ---------------------------------------------------------------------------


class TestUserRegistrationAndAuth:
    """Corresponds to the 'User Registration & Authentication' section."""

    def test_register_creates_user(self):
        client = _fresh_client()
        ts = int(time.time() * 1000)
        username = f"integration_reg_{ts}"
        resp = client.post(
            "/api/v1/users/register",
            json={
                "username": username,
                "email": f"{username}@example.com",
                "password": "testpass123",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["username"] == username

    def test_login_returns_token(self):
        client = _fresh_client()
        headers, _ = _register_and_login(client)
        assert "Authorization" in headers

    def test_me_returns_profile(self):
        client = _fresh_client()
        headers, username = _register_and_login(client)
        resp = client.get("/api/v1/users/me", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["username"] == username

    def test_me_requires_auth(self):
        client = _fresh_client()
        resp = client.get("/api/v1/users/me")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Workspace CRUD
# ---------------------------------------------------------------------------


class TestWorkspaceCRUD:
    """Corresponds to the 'Workspace CRUD' section."""

    def test_create_workspace(self):
        client = _fresh_client()
        headers, _ = _register_and_login(client)
        ts = int(time.time() * 1000)
        name = f"integration-test-ws-{ts}"

        resp = client.post(
            "/api/v1/workspaces/",
            json={"name": name},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["name"] == name

    def test_list_workspaces(self):
        client = _fresh_client()
        headers, _ = _register_and_login(client)

        # Create a workspace first
        client.post(
            "/api/v1/workspaces/",
            json={"name": f"ws-list-{int(time.time() * 1000)}"},
            headers=headers,
        )

        resp = client.get("/api/v1/workspaces/", headers=headers)
        assert resp.status_code == 200
        workspaces = resp.json()
        assert len(workspaces) >= 1

    def test_get_workspace_by_id(self):
        client = _fresh_client()
        headers, _ = _register_and_login(client)
        ts = int(time.time() * 1000)
        name = f"integration-get-ws-{ts}"

        create_resp = client.post(
            "/api/v1/workspaces/",
            json={"name": name},
            headers=headers,
        )
        ws_id = create_resp.json()["id"]

        resp = client.get(f"/api/v1/workspaces/{ws_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == name

    def test_workspace_requires_auth(self):
        client = _fresh_client()
        resp = client.get("/api/v1/workspaces/")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Notebook CRUD
# ---------------------------------------------------------------------------


class TestNotebookCRUD:
    """Corresponds to the 'Notebook CRUD' section."""

    def _setup(self, client):
        headers, _ = _register_and_login(client)
        ws = client.post(
            "/api/v1/workspaces/",
            json={"name": f"nb-ws-{int(time.time() * 1000)}"},
            headers=headers,
        ).json()
        return headers, ws

    def test_create_notebook(self):
        client = _fresh_client()
        headers, ws = self._setup(client)
        ts = int(time.time() * 1000)
        name = f"integration-test-nb-{ts}"

        resp = client.post(
            f"/api/v1/workspaces/{ws['id']}/notebooks/",
            json={"name": name},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data

    def test_list_notebooks(self):
        client = _fresh_client()
        headers, ws = self._setup(client)

        # Create a notebook first
        client.post(
            f"/api/v1/workspaces/{ws['id']}/notebooks/",
            json={"name": f"nb-list-{int(time.time() * 1000)}"},
            headers=headers,
        )

        resp = client.get(
            f"/api/v1/workspaces/{ws['id']}/notebooks/",
            headers=headers,
        )
        assert resp.status_code == 200
        notebooks = resp.json()
        assert len(notebooks) >= 1


# ---------------------------------------------------------------------------
# File Operations
# ---------------------------------------------------------------------------


class TestFileOperations:
    """Corresponds to the 'File Operations' section."""

    def _setup(self, client):
        headers, _ = _register_and_login(client)
        ws = client.post(
            "/api/v1/workspaces/",
            json={"name": f"file-ws-{int(time.time() * 1000)}"},
            headers=headers,
        ).json()
        nb = client.post(
            f"/api/v1/workspaces/{ws['id']}/notebooks/",
            json={"name": f"file-nb-{int(time.time() * 1000)}"},
            headers=headers,
        ).json()
        return headers, ws, nb

    def test_create_file(self):
        client = _fresh_client()
        headers, ws, nb = self._setup(client)

        content = (
            "---\ntitle: Integration Test File\n"
            "tags: [test, integration]\n---\n\n"
            "# Hello from integration tests\n"
        )
        resp = client.post(
            f"/api/v1/workspaces/{ws['id']}/notebooks/{nb['id']}/files/",
            json={"path": "test-file.md", "content": content},
            headers=headers,
        )
        assert resp.status_code == 200

    def test_list_files(self):
        client = _fresh_client()
        headers, ws, nb = self._setup(client)

        # Create a file first
        client.post(
            f"/api/v1/workspaces/{ws['id']}/notebooks/{nb['id']}/files/",
            json={"path": "list-test.md", "content": "# List test"},
            headers=headers,
        )

        resp = client.get(
            f"/api/v1/workspaces/{ws['id']}/notebooks/{nb['id']}/files/",
            headers=headers,
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class TestSearch:
    """Corresponds to the 'Search' section."""

    def test_search_returns_200(self):
        client = _fresh_client()
        headers, _ = _register_and_login(client)
        ws = client.post(
            "/api/v1/workspaces/",
            json={"name": f"search-ws-{int(time.time() * 1000)}"},
            headers=headers,
        ).json()
        # Create a notebook so the workspace search route has something to query
        client.post(
            f"/api/v1/workspaces/{ws['id']}/notebooks/",
            json={"name": f"search-nb-{int(time.time() * 1000)}"},
            headers=headers,
        )

        resp = client.get(
            f"/api/v1/workspaces/{ws['slug']}/search/?q=integration",
            headers=headers,
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Task Queue
# ---------------------------------------------------------------------------


class TestTaskQueue:
    """Corresponds to the 'Task Queue' section."""

    def test_list_tasks(self):
        client = _fresh_client()
        headers, _ = _register_and_login(client)
        ws = client.post(
            "/api/v1/workspaces/",
            json={"name": f"task-ws-{int(time.time() * 1000)}"},
            headers=headers,
        ).json()

        resp = client.get(
            "/api/v1/tasks/",
            params={"workspace_id": ws["id"]},
            headers=headers,
        )
        assert resp.status_code == 200

    def test_tasks_require_auth(self):
        client = _fresh_client()
        resp = client.get("/api/v1/tasks/", params={"workspace_id": 1})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Query API
# ---------------------------------------------------------------------------


class TestQueryAPI:
    """Corresponds to the 'Query API' section."""

    def test_query_returns_200(self):
        client = _fresh_client()
        headers, _ = _register_and_login(client)
        ws = client.post(
            "/api/v1/workspaces/",
            json={"name": f"query-ws-{int(time.time() * 1000)}"},
            headers=headers,
        ).json()

        resp = client.post(
            "/api/v1/query/",
            params={"workspace_id": ws["id"]},
            json={},
            headers=headers,
        )
        assert resp.status_code == 200

    def test_query_requires_auth(self):
        client = _fresh_client()
        resp = client.post("/api/v1/query/", params={"workspace_id": 1}, json={})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# CORS Headers
# ---------------------------------------------------------------------------


class TestCORS:
    """Corresponds to the 'CORS Headers' section."""

    def test_cors_headers_present(self):
        client = _fresh_client()
        resp = client.options(
            "/api/v1/users/me",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # FastAPI CORS middleware should add the header
        assert "access-control-allow-origin" in resp.headers


# ---------------------------------------------------------------------------
# Full end-to-end flow (single-test walkthrough)
# ---------------------------------------------------------------------------


class TestEndToEndFlow:
    """A single test that mirrors the complete sequential flow of the
    original shell script: register -> login -> workspace -> notebook ->
    file -> search -> tasks -> query.
    """

    def test_complete_lifecycle(self):
        client = _fresh_client()
        ts = int(time.time() * 1000)

        # 1. Register
        username = f"e2e_{ts}"
        password = "testpass123"
        email = f"{username}@example.com"

        reg = client.post(
            "/api/v1/users/register",
            json={"username": username, "email": email, "password": password},
        )
        assert reg.status_code == 201
        assert reg.json()["username"] == username

        # 2. Login
        login = client.post(
            "/api/v1/users/token",
            data={"username": username, "password": password},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        assert token
        headers = {"Authorization": f"Bearer {token}"}

        # 3. /users/me
        me = client.get("/api/v1/users/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["username"] == username

        # 4. Create workspace
        ws_name = f"e2e-ws-{ts}"
        ws_resp = client.post(
            "/api/v1/workspaces/",
            json={"name": ws_name},
            headers=headers,
        )
        assert ws_resp.status_code == 200
        ws = ws_resp.json()
        assert ws["id"]
        assert ws["name"] == ws_name

        # 5. List workspaces
        ws_list = client.get("/api/v1/workspaces/", headers=headers)
        assert ws_list.status_code == 200
        assert len(ws_list.json()) >= 1

        # 6. Get workspace by id
        ws_detail = client.get(f"/api/v1/workspaces/{ws['id']}", headers=headers)
        assert ws_detail.status_code == 200
        assert ws_detail.json()["name"] == ws_name

        # 7. Create notebook
        nb_name = f"e2e-nb-{ts}"
        nb_resp = client.post(
            f"/api/v1/workspaces/{ws['id']}/notebooks/",
            json={"name": nb_name},
            headers=headers,
        )
        assert nb_resp.status_code == 200
        nb = nb_resp.json()
        assert nb["id"]

        # 8. List notebooks
        nb_list = client.get(
            f"/api/v1/workspaces/{ws['id']}/notebooks/",
            headers=headers,
        )
        assert nb_list.status_code == 200
        assert len(nb_list.json()) >= 1

        # 9. Create file
        file_content = (
            "---\ntitle: E2E Test File\ntags: [e2e, integration]\n---\n\n"
            "# End-to-end test content\n"
        )
        file_resp = client.post(
            f"/api/v1/workspaces/{ws['id']}/notebooks/{nb['id']}/files/",
            json={"path": "e2e-test.md", "content": file_content},
            headers=headers,
        )
        assert file_resp.status_code == 200

        # 10. List files
        files_list = client.get(
            f"/api/v1/workspaces/{ws['id']}/notebooks/{nb['id']}/files/",
            headers=headers,
        )
        assert files_list.status_code == 200

        # 11. Search
        search_resp = client.get(
            f"/api/v1/workspaces/{ws['slug']}/search/?q=e2e",
            headers=headers,
        )
        assert search_resp.status_code == 200

        # 12. Task queue
        task_resp = client.get(
            "/api/v1/tasks/",
            params={"workspace_id": ws["id"]},
            headers=headers,
        )
        assert task_resp.status_code == 200

        # 13. Query API
        query_resp = client.post(
            "/api/v1/query/",
            params={"workspace_id": ws["id"]},
            json={},
            headers=headers,
        )
        assert query_resp.status_code == 200
