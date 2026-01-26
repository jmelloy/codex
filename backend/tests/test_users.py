"""Tests for user endpoints and authentication."""

import time
import pytest
from httpx import AsyncClient, ASGITransport
from codex.main import app


def test_get_current_user(test_client):
    """Test getting current user information."""
    # Register a user
    username = f"current_user_test_{int(time.time() * 1000)}"
    email = f"{username}@example.com"
    password = "testpass123"

    register_response = test_client.post("/api/register", json={"username": username, "email": email, "password": password})
    assert register_response.status_code == 201
    user_id = register_response.json()["id"]

    # Login
    login_response = test_client.post("/api/token", data={"username": username, "password": password})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Get current user
    response = test_client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    user = response.json()
    assert user["id"] == user_id
    assert user["username"] == username
    assert user["email"] == email
    assert user["is_active"] is True
    # Password should not be exposed
    assert "hashed_password" not in user or user.get("hashed_password") is None


def test_get_current_user_requires_auth(test_client):
    """Test that /users/me requires authentication."""
    response = test_client.get("/api/users/me")
    assert response.status_code == 401


def test_get_current_user_invalid_token(test_client):
    """Test that /users/me rejects invalid tokens."""
    response = test_client.get("/api/users/me", headers={"Authorization": "Bearer invalid_token_here"})
    assert response.status_code == 401


def test_login_wrong_password(test_client):
    """Test login with incorrect password."""
    # Register a user
    username = f"wrong_pass_test_{int(time.time() * 1000)}"
    email = f"{username}@example.com"
    password = "testpass123"

    test_client.post("/api/register", json={"username": username, "email": email, "password": password})

    # Try to login with wrong password
    response = test_client.post("/api/token", data={"username": username, "password": "wrongpassword"})
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


def test_login_nonexistent_user(test_client):
    """Test login with non-existent username."""
    response = test_client.post("/api/token", data={"username": "nonexistent_user_12345", "password": "somepassword"})
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


def test_token_format(test_client):
    """Test that login returns properly formatted token."""
    # Register a user
    username = f"token_format_test_{int(time.time() * 1000)}"
    email = f"{username}@example.com"
    password = "testpass123"

    test_client.post("/api/register", json={"username": username, "email": email, "password": password})

    # Login
    response = test_client.post("/api/token", data={"username": username, "password": password})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"
    # Token should be a non-empty string
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 0


@pytest.mark.asyncio
async def test_get_current_user_async():
    """Test getting current user with async client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Register a user
        username = f"async_user_test_{int(time.time() * 1000)}"
        email = f"{username}@example.com"
        password = "testpass123"

        register_response = await ac.post(
            "/api/register", json={"username": username, "email": email, "password": password}
        )
        assert register_response.status_code == 201

        # Login
        login_response = await ac.post("/api/token", data={"username": username, "password": password})
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Get current user
        response = await ac.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        user = response.json()
        assert user["username"] == username
        assert user["email"] == email


def test_multiple_logins_same_user(test_client):
    """Test that a user can have multiple valid sessions."""
    # Register a user
    username = f"multi_login_test_{int(time.time() * 1000)}"
    email = f"{username}@example.com"
    password = "testpass123"

    test_client.post("/api/register", json={"username": username, "email": email, "password": password})

    # Login multiple times
    tokens = []
    for _ in range(3):
        login_response = test_client.post("/api/token", data={"username": username, "password": password})
        assert login_response.status_code == 200
        tokens.append(login_response.json()["access_token"])

    # All tokens should work
    for token in tokens:
        response = test_client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["username"] == username
