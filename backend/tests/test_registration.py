"""Tests for user registration."""

import pytest
import time
from httpx import AsyncClient, ASGITransport
from backend.api.main import app


@pytest.mark.asyncio
async def test_user_registration():
    """Test user registration endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test successful registration with unique username
        username = f"testuser_{int(time.time() * 1000)}"
        response = await client.post(
            "/register", json={"username": username, "email": f"{username}@example.com", "password": "testpassword123"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == username
        assert data["email"] == f"{username}@example.com"
        assert data["is_active"] is True
        assert "id" in data


@pytest.mark.asyncio
async def test_duplicate_username():
    """Test registration with duplicate username."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register first user
        await client.post(
            "/register", json={"username": "duplicate", "email": "user1@example.com", "password": "password123"}
        )

        # Try to register with same username
        response = await client.post(
            "/register", json={"username": "duplicate", "email": "user2@example.com", "password": "password456"}
        )
        assert response.status_code == 400
        assert "Username already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_duplicate_email():
    """Test registration with duplicate email."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register first user
        await client.post(
            "/register", json={"username": "user1", "email": "duplicate@example.com", "password": "password123"}
        )

        # Try to register with same email
        response = await client.post(
            "/register", json={"username": "user2", "email": "duplicate@example.com", "password": "password456"}
        )
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_invalid_email():
    """Test registration with invalid email."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/register", json={"username": "testuser", "email": "invalid-email", "password": "password123"}
        )
        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_short_password():
    """Test registration with short password."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/register", json={"username": "testuser", "email": "test@example.com", "password": "short"}
        )
        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_short_username():
    """Test registration with short username."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/register", json={"username": "ab", "email": "test@example.com", "password": "password123"}
        )
        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_login_after_registration():
    """Test that a registered user can login."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register user
        await client.post(
            "/register", json={"username": "logintest", "email": "logintest@example.com", "password": "password123"}
        )

        # Try to login
        response = await client.post("/token", data={"username": "logintest", "password": "password123"})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_default_workspace_creation():
    """Test that a default workspace is created on user registration."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register a new user with a unique username
        username = f"workspace_test_user_{int(time.time() * 1000)}"
        register_response = await client.post(
            "/register", json={"username": username, "email": f"{username}@example.com", "password": "testpass123"}
        )
        assert register_response.status_code == 201
        user_data = register_response.json()
        user_id = user_data["id"]

        # Login to get access token
        login_response = await client.post("/token", data={"username": username, "password": "testpass123"})
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Check that a workspace was created
        workspaces_response = await client.get("/api/v1/workspaces/", headers=headers)
        assert workspaces_response.status_code == 200
        workspaces = workspaces_response.json()

        # Should have exactly one workspace
        assert len(workspaces) == 1

        # The workspace should be named after the username
        default_workspace = workspaces[0]
        assert default_workspace["name"] == username
        assert default_workspace["owner_id"] == user_id
