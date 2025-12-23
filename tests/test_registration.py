"""Tests for user registration."""

import pytest
from httpx import AsyncClient, ASGITransport
from backend.api.main import app
from backend.db.database import init_system_db


@pytest.mark.asyncio
async def test_user_registration():
    """Test user registration endpoint."""
    # Initialize the database
    await init_system_db()
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test successful registration
        response = await client.post(
            "/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "testpassword123"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert data["is_active"] is True
        assert "id" in data


@pytest.mark.asyncio
async def test_duplicate_username():
    """Test registration with duplicate username."""
    await init_system_db()
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register first user
        await client.post(
            "/register",
            json={
                "username": "duplicate",
                "email": "user1@example.com",
                "password": "password123"
            }
        )
        
        # Try to register with same username
        response = await client.post(
            "/register",
            json={
                "username": "duplicate",
                "email": "user2@example.com",
                "password": "password456"
            }
        )
        assert response.status_code == 400
        assert "Username already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_duplicate_email():
    """Test registration with duplicate email."""
    await init_system_db()
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register first user
        await client.post(
            "/register",
            json={
                "username": "user1",
                "email": "duplicate@example.com",
                "password": "password123"
            }
        )
        
        # Try to register with same email
        response = await client.post(
            "/register",
            json={
                "username": "user2",
                "email": "duplicate@example.com",
                "password": "password456"
            }
        )
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_invalid_email():
    """Test registration with invalid email."""
    await init_system_db()
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/register",
            json={
                "username": "testuser",
                "email": "invalid-email",
                "password": "password123"
            }
        )
        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_short_password():
    """Test registration with short password."""
    await init_system_db()
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "short"
            }
        )
        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_short_username():
    """Test registration with short username."""
    await init_system_db()
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/register",
            json={
                "username": "ab",
                "email": "test@example.com",
                "password": "password123"
            }
        )
        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_login_after_registration():
    """Test that a registered user can login."""
    await init_system_db()
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register user
        await client.post(
            "/register",
            json={
                "username": "logintest",
                "email": "logintest@example.com",
                "password": "password123"
            }
        )
        
        # Try to login
        response = await client.post(
            "/token",
            data={
                "username": "logintest",
                "password": "password123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
