"""Tests for v1 user endpoints."""

import time

import pytest
from httpx import ASGITransport, AsyncClient

from codex.main import app


def test_v1_get_current_user(test_client):
    """Test getting current user information via v1 endpoint."""
    # Register a user
    username = f"v1_current_user_test_{int(time.time() * 1000)}"
    email = f"{username}@example.com"
    password = "testpass123"

    register_response = test_client.post(
        "/api/v1/users/register", json={"username": username, "email": email, "password": password}
    )
    assert register_response.status_code == 201
    user_id = register_response.json()["id"]

    # Login via v1
    login_response = test_client.post("/api/v1/users/token", data={"username": username, "password": password})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Get current user via v1
    response = test_client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    user = response.json()
    assert user["id"] == user_id
    assert user["username"] == username
    assert user["email"] == email
    assert user["is_active"] is True


def test_v1_get_current_user_requires_auth(test_client):
    """Test that v1 /me requires authentication."""
    response = test_client.get("/api/v1/users/me")
    assert response.status_code == 401


def test_v1_login_wrong_password(test_client):
    """Test v1 login with incorrect password."""
    # Register a user
    username = f"v1_wrong_pass_test_{int(time.time() * 1000)}"
    email = f"{username}@example.com"
    password = "testpass123"

    test_client.post("/api/v1/users/register", json={"username": username, "email": email, "password": password})

    # Try to login with wrong password via v1
    response = test_client.post("/api/v1/users/token", data={"username": username, "password": "wrongpassword"})
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


def test_v1_token_format(test_client):
    """Test that v1 login returns properly formatted token."""
    # Register a user
    username = f"v1_token_format_test_{int(time.time() * 1000)}"
    email = f"{username}@example.com"
    password = "testpass123"

    test_client.post("/api/v1/users/register", json={"username": username, "email": email, "password": password})

    # Login via v1
    response = test_client.post("/api/v1/users/token", data={"username": username, "password": password})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 0


def test_v1_backward_compatibility(test_client):
    """Test that both v1 and legacy endpoints work with the same user."""
    # Register via legacy endpoint
    username = f"v1_compat_test_{int(time.time() * 1000)}"
    email = f"{username}@example.com"
    password = "testpass123"

    test_client.post("/api/register", json={"username": username, "email": email, "password": password})

    # Login via v1 endpoint
    v1_login = test_client.post("/api/v1/users/token", data={"username": username, "password": password})
    assert v1_login.status_code == 200
    v1_token = v1_login.json()["access_token"]

    # Access user info via v1 endpoint
    v1_user = test_client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {v1_token}"})
    assert v1_user.status_code == 200
    assert v1_user.json()["username"] == username

    # Login via legacy endpoint
    legacy_login = test_client.post("/api/token", data={"username": username, "password": password})
    assert legacy_login.status_code == 200
    legacy_token = legacy_login.json()["access_token"]

    # Access user info via legacy endpoint
    legacy_user = test_client.get("/api/users/me", headers={"Authorization": f"Bearer {legacy_token}"})
    assert legacy_user.status_code == 200
    assert legacy_user.json()["username"] == username

    # Cross-use tokens: v1 token with legacy endpoint
    cross1 = test_client.get("/api/users/me", headers={"Authorization": f"Bearer {v1_token}"})
    assert cross1.status_code == 200

    # Legacy token with v1 endpoint
    cross2 = test_client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {legacy_token}"})
    assert cross2.status_code == 200


@pytest.mark.asyncio
async def test_v1_get_current_user_async():
    """Test getting current user with async client via v1 endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Register a user via v1
        username = f"v1_async_user_test_{int(time.time() * 1000)}"
        email = f"{username}@example.com"
        password = "testpass123"

        register_response = await ac.post(
            "/api/v1/users/register", json={"username": username, "email": email, "password": password}
        )
        assert register_response.status_code == 201

        # Login via v1
        login_response = await ac.post("/api/v1/users/token", data={"username": username, "password": password})
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Get current user via v1
        response = await ac.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        user = response.json()
        assert user["username"] == username
        assert user["email"] == email
