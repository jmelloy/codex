"""Test weather-api integration plugin."""

import pytest
from fastapi.testclient import TestClient

from codex.main import app


@pytest.fixture
def client():
    """Create test client with lifespan context."""
    with TestClient(app) as client:
        yield client


def test_weather_integration_is_loaded(client):
    """Test that weather-api integration is loaded."""
    # Create a test user
    import time
    username = f"testuser_weather_{int(time.time() * 1000)}"
    
    response = client.post(
        "/api/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "testpass123",
        },
    )
    assert response.status_code == 201

    response = client.post(
        "/api/token", data={"username": username, "password": "testpass123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # List integrations
    response = client.get("/api/v1/integrations", headers=headers)
    assert response.status_code == 200
    integrations = response.json()
    
    # Find weather-api
    weather = next((i for i in integrations if i["id"] == "weather-api"), None)
    assert weather is not None
    assert weather["name"] == "Weather API Integration"
    assert weather["api_type"] == "rest"
    assert weather["base_url"] == "https://api.openweathermap.org/data/2.5"
    assert weather["auth_method"] == "api_key"


def test_weather_integration_details(client):
    """Test getting weather-api integration details."""
    # Create a test user
    import time
    username = f"testuser_weather_{int(time.time() * 1000)}"
    
    response = client.post(
        "/api/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "testpass123",
        },
    )
    assert response.status_code == 201

    response = client.post(
        "/api/token", data={"username": username, "password": "testpass123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get integration details
    response = client.get("/api/v1/integrations/weather-api", headers=headers)
    assert response.status_code == 200
    
    weather = response.json()
    assert weather["id"] == "weather-api"
    assert weather["name"] == "Weather API Integration"
    assert weather["version"] == "1.0.0"
    assert weather["author"] == "Codex Team"


def test_weather_integration_blocks(client):
    """Test getting weather-api block definitions."""
    # Create a test user
    import time
    username = f"testuser_weather_{int(time.time() * 1000)}"
    
    response = client.post(
        "/api/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "testpass123",
        },
    )
    assert response.status_code == 201

    response = client.post(
        "/api/token", data={"username": username, "password": "testpass123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get blocks
    response = client.get("/api/v1/integrations/weather-api/blocks", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["integration_id"] == "weather-api"
    assert len(data["blocks"]) == 1
    
    weather_block = data["blocks"][0]
    assert weather_block["id"] == "weather"
    assert weather_block["name"] == "Weather Block"
    assert weather_block["icon"] == "☀️"
