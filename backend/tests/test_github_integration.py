"""Test github integration plugin."""

import time

import pytest
from fastapi.testclient import TestClient

from codex.main import app


@pytest.fixture
def client():
    """Create test client with lifespan context."""
    with TestClient(app) as client:
        yield client


def _create_user_and_get_headers(client):
    username = f"testuser_github_{int(time.time() * 1000)}"
    response = client.post(
        "/api/v1/users/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "testpass123",
        },
    )
    assert response.status_code == 201

    response = client.post("/api/v1/users/token", data={"username": username, "password": "testpass123"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_github_integration_is_loaded(client):
    """Test that github integration is loaded."""
    headers = _create_user_and_get_headers(client)

    response = client.get("/api/v1/plugins/integrations", headers=headers)
    assert response.status_code == 200
    integrations = response.json()

    github = next((i for i in integrations if i["id"] == "github"), None)
    assert github is not None
    assert github["name"] == "GitHub Integration"
    assert github["api_type"] == "rest"
    assert github["base_url"] == "https://api.github.com"
    assert github["auth_method"] == "token"


def test_github_integration_details(client):
    """Test getting github integration details."""
    headers = _create_user_and_get_headers(client)

    response = client.get("/api/v1/plugins/integrations/github", headers=headers)
    assert response.status_code == 200

    github = response.json()
    assert github["id"] == "github"
    assert github["name"] == "GitHub Integration"
    assert github["version"] == "1.0.0"
    assert github["author"] == "Codex Team"


def test_github_integration_blocks(client):
    """Test getting github block definitions."""
    headers = _create_user_and_get_headers(client)

    response = client.get("/api/v1/plugins/integrations/github/blocks", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["integration_id"] == "github"
    assert len(data["blocks"]) == 3

    block_ids = {b["id"] for b in data["blocks"]}
    assert "github-issues" in block_ids
    assert "github-pulls" in block_ids
    assert "github-repo" in block_ids


def test_github_integration_endpoints(client):
    """Test that github integration has the expected endpoints."""
    headers = _create_user_and_get_headers(client)

    response = client.get("/api/v1/plugins/integrations/github", headers=headers)
    assert response.status_code == 200

    github = response.json()
    endpoint_ids = {ep["id"] for ep in github.get("endpoints", [])}
    assert "get_user" in endpoint_ids
    assert "list_issues" in endpoint_ids
    assert "list_pulls" in endpoint_ids
    assert "get_repo" in endpoint_ids
