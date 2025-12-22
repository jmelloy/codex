"""Tests for authentication system."""

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from core.workspace import Workspace
from db.models import User, get_engine, get_session


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
            "password": "testpassword123"
        }
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
    # Register first user
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test1@example.com",
            "password": "testpassword123"
        }
    )
    
    # Try to register with same username
    response = client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test2@example.com",
            "password": "testpassword456"
        }
    )
    
    assert response.status_code == 400
    assert "Username already registered" in response.json()["detail"]


def test_register_duplicate_email(client, temp_workspace):
    """Test registering with a duplicate email."""
    # Register first user
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser1",
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    
    # Try to register with same email
    response = client.post(
        "/api/auth/register",
        json={
            "username": "testuser2",
            "email": "test@example.com",
            "password": "testpassword456"
        }
    )
    
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


def test_login_user(client, temp_workspace):
    """Test user login."""
    # Register a user
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    
    # Login
    response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "testpassword123"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "testuser"


def test_login_wrong_password(client, temp_workspace):
    """Test login with wrong password."""
    # Register a user
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    
    # Try to login with wrong password
    response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "wrongpassword"
        }
    )
    
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


def test_login_nonexistent_user(client, temp_workspace):
    """Test login with nonexistent user."""
    response = client.post(
        "/api/auth/login",
        json={
            "username": "nonexistent",
            "password": "testpassword123"
        }
    )
    
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


def test_get_current_user(client, temp_workspace):
    """Test getting current user info."""
    # Register and get token
    register_response = client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    token = register_response.json()["access_token"]
    
    # Get current user
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "password" not in data


def test_authenticated_endpoint_without_token(client, temp_workspace):
    """Test accessing authenticated endpoint without token."""
    response = client.get("/api/notebooks")
    
    assert response.status_code == 401


def test_authenticated_endpoint_with_invalid_token(client, temp_workspace):
    """Test accessing authenticated endpoint with invalid token."""
    response = client.get(
        "/api/notebooks",
        headers={"Authorization": "Bearer invalid_token"}
    )
    
    assert response.status_code == 401


def test_authenticated_endpoint_with_valid_token(client, temp_workspace):
    """Test accessing authenticated endpoint with valid token."""
    # Register and get token
    register_response = client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    token = register_response.json()["access_token"]
    
    # Access notebooks endpoint
    response = client.get(
        "/api/notebooks",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_user_workspace_isolation(client, temp_workspace):
    """Test that users have isolated workspaces."""
    # Register first user
    response1 = client.post(
        "/api/auth/register",
        json={
            "username": "user1",
            "email": "user1@example.com",
            "password": "password123"
        }
    )
    token1 = response1.json()["access_token"]
    workspace1 = response1.json()["user"]["workspace_path"]
    
    # Register second user
    response2 = client.post(
        "/api/auth/register",
        json={
            "username": "user2",
            "email": "user2@example.com",
            "password": "password123"
        }
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
    # Register and get token
    register_response = client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    token = register_response.json()["access_token"]
    
    # Create a notebook
    response = client.post(
        "/api/notebooks",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Test Notebook",
            "description": "A test notebook"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Notebook"
    assert data["description"] == "A test notebook"
    assert "id" in data
