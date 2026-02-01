"""Pytest configuration for Docker integration tests."""

import os
import time

import pytest
import requests

# Backend URL for Docker tests
BACKEND_URL = os.environ.get("CODEX_TEST_URL", "http://localhost:8766")


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "docker: mark test as requiring Docker backend")


@pytest.fixture(scope="session")
def backend_url():
    """Get the backend URL for tests."""
    return BACKEND_URL


@pytest.fixture(scope="session")
def wait_for_backend(backend_url):
    """Wait for backend to become available (session-scoped)."""
    max_wait = 60
    start = time.time()
    while time.time() - start < max_wait:
        try:
            response = requests.get(f"{backend_url}/health", timeout=5)
            if response.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(2)
    pytest.fail(f"Backend not available at {backend_url} after {max_wait} seconds")


@pytest.fixture
def create_user(backend_url):
    """Factory fixture to create test users."""
    created_users = []

    def _create_user(username_prefix="test"):
        username = f"{username_prefix}_{int(time.time() * 1000)}"
        response = requests.post(
            f"{backend_url}/api/register",
            json={
                "username": username,
                "email": f"{username}@example.com",
                "password": "testpass123",
            },
        )
        assert response.status_code == 201, f"Failed to create user: {response.text}"
        created_users.append(username)
        return username

    yield _create_user

    # Cleanup could be added here if needed


@pytest.fixture
def get_auth_token(backend_url):
    """Factory fixture to get auth tokens."""

    def _get_token(username, password="testpass123"):
        response = requests.post(
            f"{backend_url}/api/token",
            data={"username": username, "password": password},
        )
        assert response.status_code == 200, f"Failed to get token: {response.text}"
        return response.json()["access_token"]

    return _get_token


@pytest.fixture
def authenticated_session(backend_url, create_user, get_auth_token):
    """Create an authenticated requests session."""
    username = create_user("session")
    token = get_auth_token(username)

    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {token}"
    session.base_url = backend_url

    # Add a helper method for making requests
    original_request = session.request

    def request_with_base(method, url, **kwargs):
        if not url.startswith("http"):
            url = f"{backend_url}{url}"
        return original_request(method, url, **kwargs)

    session.request = request_with_base

    return session


@pytest.fixture
def create_workspace(backend_url):
    """Factory fixture to create workspaces."""
    created_workspaces = []

    def _create_workspace(auth_headers, name_prefix="Test WS"):
        workspace_name = f"{name_prefix} {int(time.time())}"
        workspace_path = f"/tmp/test_ws_{int(time.time())}"

        response = requests.post(
            f"{backend_url}/api/v1/workspaces",
            headers=auth_headers,
            json={
                "name": workspace_name,
                "path": workspace_path,
            },
        )
        assert response.status_code == 200, f"Failed to create workspace: {response.text}"
        workspace = response.json()
        created_workspaces.append(workspace)
        return workspace

    yield _create_workspace


@pytest.fixture
def create_notebook(backend_url):
    """Factory fixture to create notebooks."""

    def _create_notebook(auth_headers, workspace_id, name_prefix="Test Notebook"):
        notebook_name = f"{name_prefix} {int(time.time())}"

        response = requests.post(
            f"{backend_url}/api/v1/notebooks",
            headers=auth_headers,
            json={
                "name": notebook_name,
                "workspace_id": workspace_id,
            },
        )
        assert response.status_code == 200, f"Failed to create notebook: {response.text}"
        return response.json()

    return _create_notebook
