"""Integration tests for search API endpoints."""

import time


def test_search_returns_results_structure(test_client, auth_headers, workspace_and_notebook):
    """Test that search endpoint returns proper structure."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

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


def test_search_with_empty_query(test_client, auth_headers, workspace_and_notebook):
    """Test search with empty query parameter."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Search with empty query (should still work, returning empty results)
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/search/?q=",
        headers=headers,
    )
    # The endpoint should handle empty queries gracefully
    assert response.status_code in [200, 422]  # 422 for validation error is also acceptable


def test_search_nonexistent_workspace(test_client, auth_headers):
    """Test search in a workspace that doesn't exist."""
    headers = auth_headers[0]

    response = test_client.get(
        "/api/v1/workspaces/99999/search/?q=test",
        headers=headers,
    )
    assert response.status_code == 404
    assert "Workspace not found" in response.json()["detail"]


def test_search_other_users_workspace(test_client, auth_headers, workspace_and_notebook):
    """Test that users cannot search in other users' workspaces."""
    workspace, _ = workspace_and_notebook

    # Create second user
    username2 = f"test_search_user2_{int(time.time() * 1000)}"
    test_client.post(
        "/api/v1/users/register",
        json={"username": username2, "email": f"{username2}@example.com", "password": "testpass123"},
    )
    login_response = test_client.post("/api/v1/users/token", data={"username": username2, "password": "testpass123"})
    headers2 = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    # Try to search in first user's workspace
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/search/?q=test",
        headers=headers2,
    )
    assert response.status_code == 404


def test_search_by_tags_returns_structure(test_client, auth_headers, workspace_and_notebook):
    """Test that tag search endpoint returns proper structure."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

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


def test_search_by_single_tag(test_client, auth_headers, workspace_and_notebook):
    """Test search with a single tag."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/search/tags?tags=documentation",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tags"] == ["documentation"]


def test_search_by_tags_strips_whitespace(test_client, auth_headers, workspace_and_notebook):
    """Test that tag search strips whitespace from tags."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/search/tags?tags=  python  ,  testing  ",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tags"] == ["python", "testing"]


def test_search_by_tags_nonexistent_workspace(test_client, auth_headers):
    """Test tag search in a workspace that doesn't exist."""
    headers = auth_headers[0]

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


def test_search_requires_workspace_id(test_client, auth_headers):
    """Test that search requires workspace parameter in path."""
    headers = auth_headers[0]

    # Invalid workspace slug/id should return 404
    response = test_client.get(
        "/api/v1/workspaces/nonexistent/search/?q=test",
        headers=headers,
    )
    assert response.status_code == 404


def test_search_tags_requires_tags_parameter(test_client, auth_headers, workspace_and_notebook):
    """Test that tag search requires tags parameter."""
    headers = auth_headers[0]
    workspace, _ = workspace_and_notebook

    # Missing tags parameter
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/search/tags",
        headers=headers,
    )
    assert response.status_code == 422  # Validation error
