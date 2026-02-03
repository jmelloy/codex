"""Integration tests for search API endpoints."""

import time


def setup_test_user(test_client):
    """Register and login a test user."""
    username = f"test_search_user_{int(time.time() * 1000)}"
    email = f"{username}@example.com"
    password = "testpass123"

    test_client.post("/api/v1/users/register", json={"username": username, "email": email, "password": password})
    login_response = test_client.post("/api/v1/users/token", data={"username": username, "password": password})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, username


def setup_workspace_and_notebook(test_client, headers, temp_workspace_dir):
    """Create a workspace and notebook for testing."""
    # Create workspace
    ws_response = test_client.post(
        "/api/v1/workspaces/",
        json={"name": "Test Search Workspace", "path": temp_workspace_dir},
        headers=headers,
    )
    assert ws_response.status_code == 200
    workspace = ws_response.json()

    # Create notebook using nested route
    nb_response = test_client.post(
        f"/api/v1/workspaces/{workspace['id']}/notebooks/",
        json={"name": "Test Notebook"},
        headers=headers,
    )
    assert nb_response.status_code == 200
    notebook = nb_response.json()

    return workspace, notebook


def test_search_returns_results_structure(test_client, temp_workspace_dir):
    """Test that search endpoint returns proper structure."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Perform search using nested route with workspace slug
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/search/?q=test",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert "workspace_id" in data
    assert "workspace_slug" in data
    assert "results" in data
    assert data["query"] == "test"
    assert data["workspace_id"] == workspace["id"]
    assert data["workspace_slug"] == workspace["slug"]
    assert isinstance(data["results"], list)


def test_search_with_empty_query(test_client, temp_workspace_dir):
    """Test search with empty query parameter."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Search with empty query (should still work, returning empty results)
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/search/?q=",
        headers=headers,
    )
    # The endpoint should handle empty queries gracefully
    assert response.status_code in [200, 422]  # 422 for validation error is also acceptable


def test_search_nonexistent_workspace(test_client, temp_workspace_dir):
    """Test search in a workspace that doesn't exist."""
    headers, _ = setup_test_user(test_client)

    response = test_client.get(
        "/api/v1/workspaces/99999/search/?q=test",
        headers=headers,
    )
    assert response.status_code == 404
    assert "Workspace not found" in response.json()["detail"]


def test_search_other_users_workspace(test_client, temp_workspace_dir):
    """Test that users cannot search in other users' workspaces."""
    # Create first user and workspace
    headers1, _ = setup_test_user(test_client)
    workspace, _ = setup_workspace_and_notebook(test_client, headers1, temp_workspace_dir)

    # Create second user
    headers2, _ = setup_test_user(test_client)

    # Try to search in first user's workspace
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/search/?q=test",
        headers=headers2,
    )
    assert response.status_code == 404


def test_search_by_tags_returns_structure(test_client, temp_workspace_dir):
    """Test that tag search endpoint returns proper structure."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Perform tag search using nested route
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/search/tags?tags=python,testing",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "tags" in data
    assert "workspace_id" in data
    assert "workspace_slug" in data
    assert "results" in data
    assert data["tags"] == ["python", "testing"]
    assert data["workspace_id"] == workspace["id"]
    assert data["workspace_slug"] == workspace["slug"]
    assert isinstance(data["results"], list)


def test_search_by_single_tag(test_client, temp_workspace_dir):
    """Test search with a single tag."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/search/tags?tags=documentation",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tags"] == ["documentation"]


def test_search_by_tags_strips_whitespace(test_client, temp_workspace_dir):
    """Test that tag search strips whitespace from tags."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/search/tags?tags=  python  ,  testing  ",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tags"] == ["python", "testing"]


def test_search_by_tags_nonexistent_workspace(test_client, temp_workspace_dir):
    """Test tag search in a workspace that doesn't exist."""
    headers, _ = setup_test_user(test_client)

    response = test_client.get(
        "/api/v1/workspaces/99999/search/tags?tags=test",
        headers=headers,
    )
    assert response.status_code == 404
    assert "Workspace not found" in response.json()["detail"]


def test_search_requires_authentication(test_client):
    """Test that search endpoints require authentication."""
    response = test_client.get("/api/v1/workspaces/1/search/?q=test")
    assert response.status_code == 401

    response = test_client.get("/api/v1/workspaces/1/search/tags?tags=test")
    assert response.status_code == 401


def test_search_requires_workspace_id(test_client, temp_workspace_dir):
    """Test that search requires workspace parameter in path."""
    headers, _ = setup_test_user(test_client)

    # Invalid workspace slug/id should return 404
    response = test_client.get(
        "/api/v1/workspaces/nonexistent/search/?q=test",
        headers=headers,
    )
    assert response.status_code == 404


def test_search_tags_requires_tags_parameter(test_client, temp_workspace_dir):
    """Test that tag search requires tags parameter."""
    headers, _ = setup_test_user(test_client)
    workspace, _ = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Missing tags parameter
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/search/tags",
        headers=headers,
    )
    assert response.status_code == 422  # Validation error
