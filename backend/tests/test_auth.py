"""Tests for authentication system."""

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from core.workspace import Workspace


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_path = Path(tmpdir) / "test_workspace"
        Workspace.initialize(workspace_path, "Test Workspace")

        # Set environment variable so the API uses this workspace
        old_workspace = os.environ.get("CODEX_WORKSPACE_PATH")
        os.environ["CODEX_WORKSPACE_PATH"] = str(workspace_path)

        yield workspace_path

        # Restore old environment variable
        if old_workspace:
            os.environ["CODEX_WORKSPACE_PATH"] = old_workspace
        else:
            os.environ.pop("CODEX_WORKSPACE_PATH", None)


@pytest.fixture
def client(temp_workspace):
    """Create a test client."""
    return TestClient(app)


def test_register_user(client, temp_workspace):
    """Test user registration."""
    import uuid

    unique_username = f"testuser_{uuid.uuid4().hex[:8]}"

    response = client.post(
        "/api/auth/register",
        json={
            "username": unique_username,
            "email": f"{unique_username}@example.com",
            "password": "testpassword123",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == unique_username
    assert f"{unique_username}@example.com" in data["user"]["email"]
    assert "password" not in data["user"]


def test_register_duplicate_username(client, temp_workspace):
    """Test registering with a duplicate username."""
    import uuid

    username = f"testuser_{uuid.uuid4().hex[:8]}"
    email1 = f"test1_{uuid.uuid4().hex[:8]}@example.com"
    email2 = f"test2_{uuid.uuid4().hex[:8]}@example.com"

    # Register first user
    client.post(
        "/api/auth/register",
        json={"username": username, "email": email1, "password": "testpassword123"},
    )

    # Try to register with same username
    response = client.post(
        "/api/auth/register",
        json={"username": username, "email": email2, "password": "testpassword456"},
    )

    assert response.status_code == 400
    assert "Username already registered" in response.json()["detail"]


def test_register_duplicate_email(client, temp_workspace):
    """Test registering with a duplicate email."""
    import uuid

    email = f"test_{uuid.uuid4().hex[:8]}@example.com"

    # Register first user
    client.post(
        "/api/auth/register",
        json={
            "username": f"testuser1_{uuid.uuid4().hex[:8]}",
            "email": email,
            "password": "testpassword123",
        },
    )

    # Try to register with same email
    response = client.post(
        "/api/auth/register",
        json={
            "username": f"testuser2_{uuid.uuid4().hex[:8]}",
            "email": email,
            "password": "testpassword456",
        },
    )

    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


def test_login_user(client, temp_workspace):
    """Test user login."""
    import uuid

    username = f"testuser_{uuid.uuid4().hex[:8]}"

    # Register a user
    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "testpassword123",
        },
    )

    # Login
    response = client.post(
        "/api/auth/login", json={"username": username, "password": "testpassword123"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == username


def test_login_wrong_password(client, temp_workspace):
    """Test login with wrong password."""
    import uuid

    username = f"testuser_{uuid.uuid4().hex[:8]}"

    # Register a user
    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "testpassword123",
        },
    )

    # Try to login with wrong password
    response = client.post(
        "/api/auth/login", json={"username": username, "password": "wrongpassword"}
    )

    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


def test_login_nonexistent_user(client, temp_workspace):
    """Test login with nonexistent user."""
    response = client.post(
        "/api/auth/login",
        json={"username": "nonexistent", "password": "testpassword123"},
    )

    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


def test_get_current_user(client, temp_workspace):
    """Test getting current user info."""
    import uuid

    username = f"testuser_{uuid.uuid4().hex[:8]}"

    # Register and get token
    register_response = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "testpassword123",
        },
    )
    token = register_response.json()["access_token"]

    # Get current user
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == username
    assert data["email"] == f"{username}@example.com"
    assert "password" not in data


def test_authenticated_endpoint_without_token(client, temp_workspace):
    """Test accessing authenticated endpoint without token."""
    response = client.get("/api/notebooks")

    assert response.status_code == 401


def test_authenticated_endpoint_with_invalid_token(client, temp_workspace):
    """Test accessing authenticated endpoint with invalid token."""
    response = client.get(
        "/api/notebooks", headers={"Authorization": "Bearer invalid_token"}
    )

    assert response.status_code == 401


def test_authenticated_endpoint_with_valid_token(client, temp_workspace):
    """Test accessing authenticated endpoint with valid token."""
    import uuid

    username = f"testuser_{uuid.uuid4().hex[:8]}"

    # Register and get token
    register_response = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "testpassword123",
        },
    )
    token = register_response.json()["access_token"]

    # Access notebooks endpoint
    response = client.get(
        "/api/notebooks", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_user_workspace_isolation(client, temp_workspace):
    """Test that users have isolated workspaces."""
    import uuid

    # Register first user
    username1 = f"user1_{uuid.uuid4().hex[:8]}"
    response1 = client.post(
        "/api/auth/register",
        json={
            "username": username1,
            "email": f"{username1}@example.com",
            "password": "password123",
        },
    )
    token1 = response1.json()["access_token"]
    workspace1 = response1.json()["user"]["workspace_path"]

    # Register second user
    username2 = f"user2_{uuid.uuid4().hex[:8]}"
    response2 = client.post(
        "/api/auth/register",
        json={
            "username": username2,
            "email": f"{username2}@example.com",
            "password": "password123",
        },
    )
    token2 = response2.json()["access_token"]
    workspace2 = response2.json()["user"]["workspace_path"]

    # Workspaces should be different
    assert workspace1 != workspace2

    # Each workspace should exist
    assert Path(workspace1).exists()
    assert Path(workspace2).exists()


def test_create_notebook_with_auth(client, temp_workspace):
    """Test creating a notebook with authentication."""
    import uuid

    username = f"testuser_{uuid.uuid4().hex[:8]}"

    # Register and get token
    register_response = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "testpassword123",
        },
    )
    token = register_response.json()["access_token"]

    # Create a notebook
    response = client.post(
        "/api/notebooks",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Test Notebook", "description": "A test notebook"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Notebook"
    assert data["description"] == "A test notebook"
    assert "id" in data


def test_register_returns_refresh_token(client, temp_workspace):
    """Test that registration returns a refresh token."""
    import uuid

    username = f"testuser_{uuid.uuid4().hex[:8]}"

    response = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "testpassword123",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["refresh_token"]) > 0


def test_login_returns_refresh_token(client, temp_workspace):
    """Test that login returns a refresh token."""
    import uuid

    username = f"testuser_{uuid.uuid4().hex[:8]}"

    # Register a user
    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "testpassword123",
        },
    )

    # Login
    response = client.post(
        "/api/auth/login", json={"username": username, "password": "testpassword123"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_refresh_token_endpoint(client, temp_workspace):
    """Test the refresh token endpoint."""
    import uuid

    username = f"testuser_{uuid.uuid4().hex[:8]}"

    # Register a user
    register_response = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "testpassword123",
        },
    )

    refresh_token = register_response.json()["refresh_token"]

    # Use refresh token to get new access token
    response = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    # Verify the token is a valid JWT by checking it has 3 parts
    assert len(data["access_token"].split(".")) == 3


def test_refresh_token_with_invalid_token(client, temp_workspace):
    """Test refresh token endpoint with invalid token."""
    response = client.post(
        "/api/auth/refresh", json={"refresh_token": "invalid_token_here"}
    )

    assert response.status_code == 401
    assert "Invalid or expired refresh token" in response.json()["detail"]


def test_refresh_token_can_access_protected_endpoints(client, temp_workspace):
    """Test that refreshed access token can access protected endpoints."""
    import uuid

    username = f"testuser_{uuid.uuid4().hex[:8]}"

    # Register a user
    register_response = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "testpassword123",
        },
    )

    refresh_token = register_response.json()["refresh_token"]

    # Use refresh token to get new access token
    refresh_response = client.post(
        "/api/auth/refresh", json={"refresh_token": refresh_token}
    )

    new_access_token = refresh_response.json()["access_token"]

    # Use new access token to access protected endpoint
    response = client.get(
        "/api/notebooks", headers={"Authorization": f"Bearer {new_access_token}"}
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_access_token_has_short_expiry(client, temp_workspace):
    """Test that access tokens have a short expiry time (15 minutes)."""
    import uuid
    from datetime import datetime, timezone
    from jose import jwt
    from api.auth import SECRET_KEY, ALGORITHM

    username = f"testuser_{uuid.uuid4().hex[:8]}"

    # Register a user
    response = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "testpassword123",
        },
    )

    access_token = response.json()["access_token"]

    # Decode the token to check expiry
    payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])

    # Check that the token has an expiry
    assert "exp" in payload

    # Calculate the difference between expiry and now
    exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    now = datetime.now(timezone.utc)
    time_diff_minutes = (exp_time - now).total_seconds() / 60

    # Should be approximately 15 minutes (allow some margin)
    assert 14 < time_diff_minutes < 16, f"Expected ~15 minutes, got {time_diff_minutes}"
