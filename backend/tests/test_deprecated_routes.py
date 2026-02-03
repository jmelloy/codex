"""Tests for deprecated routes returning 410 Gone."""

import time


def setup_test_user(test_client):
    """Register and login a test user."""
    username = f"test_deprecated_{int(time.time() * 1000)}"
    email = f"{username}@example.com"
    password = "testpass123"

    test_client.post("/api/register", json={"username": username, "email": email, "password": password})
    login_response = test_client.post("/api/token", data={"username": username, "password": password})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, username


def test_search_deprecated(test_client):
    """Test that old search endpoint returns 410 Gone."""
    headers, _ = setup_test_user(test_client)
    
    response = test_client.get("/api/v1/search/?q=test&workspace_id=1", headers=headers)
    assert response.status_code == 410
    assert "removed" in response.json()["detail"].lower()


def test_search_tags_deprecated(test_client):
    """Test that old search tags endpoint returns 410 Gone."""
    headers, _ = setup_test_user(test_client)
    
    response = test_client.get("/api/v1/search/tags?tags=test&workspace_id=1", headers=headers)
    assert response.status_code == 410
    assert "removed" in response.json()["detail"].lower()


def test_folder_get_deprecated(test_client):
    """Test that old folder GET endpoint returns 410 Gone."""
    headers, _ = setup_test_user(test_client)
    
    response = test_client.get("/api/v1/folders/test?notebook_id=1&workspace_id=1", headers=headers)
    assert response.status_code == 410
    assert "removed" in response.json()["detail"].lower()


def test_folder_put_deprecated(test_client):
    """Test that old folder PUT endpoint returns 410 Gone."""
    headers, _ = setup_test_user(test_client)
    
    response = test_client.put(
        "/api/v1/folders/test?notebook_id=1&workspace_id=1",
        json={"properties": {}},
        headers=headers
    )
    assert response.status_code == 410
    assert "removed" in response.json()["detail"].lower()


def test_folder_delete_deprecated(test_client):
    """Test that old folder DELETE endpoint returns 410 Gone."""
    headers, _ = setup_test_user(test_client)
    
    response = test_client.delete("/api/v1/folders/test?notebook_id=1&workspace_id=1", headers=headers)
    assert response.status_code == 410
    assert "removed" in response.json()["detail"].lower()
