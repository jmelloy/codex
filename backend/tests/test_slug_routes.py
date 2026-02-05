"""Test slug-based URL routing for workspaces and notebooks."""


def test_workspace_slug_creation(test_client, auth_headers):
    """Test that creating a workspace generates a slug."""
    headers = auth_headers[0]

    # Create workspace
    workspace_response = test_client.post(
        "/api/v1/workspaces/",
        headers=headers,
        json={"name": "My Test Workspace"},
    )
    assert workspace_response.status_code == 200
    workspace = workspace_response.json()

    # Verify slug was generated (may have suffix if collision occurred)
    assert "slug" in workspace
    assert workspace["slug"].startswith("my-test-workspace")
    assert workspace["name"] == "My Test Workspace"


def test_workspace_get_by_slug(test_client, auth_headers):
    """Test getting a workspace by slug."""
    headers = auth_headers[0]

    # Create workspace
    workspace_response = test_client.post(
        "/api/v1/workspaces/",
        headers=headers,
        json={"name": "Slug Test Workspace"},
    )
    workspace = workspace_response.json()
    slug = workspace["slug"]
    workspace_id = workspace["id"]

    # Get by slug
    get_by_slug_response = test_client.get(
        f"/api/v1/workspaces/{slug}",
        headers=headers,
    )
    assert get_by_slug_response.status_code == 200
    retrieved_workspace = get_by_slug_response.json()
    assert retrieved_workspace["id"] == workspace_id
    assert retrieved_workspace["slug"] == slug

    # Get by ID (should still work)
    get_by_id_response = test_client.get(
        f"/api/v1/workspaces/{workspace_id}",
        headers=headers,
    )
    assert get_by_id_response.status_code == 200
    assert get_by_id_response.json()["id"] == workspace_id


def test_nested_notebook_creation(test_client, auth_headers):
    """Test creating a notebook using the new nested URL structure."""
    headers = auth_headers[0]

    # Create workspace
    workspace_response = test_client.post(
        "/api/v1/workspaces/",
        headers=headers,
        json={"name": "Notebook Test Workspace"},
    )
    workspace = workspace_response.json()
    workspace_slug = workspace["slug"]

    # Create notebook using nested route
    notebook_response = test_client.post(
        f"/api/v1/workspaces/{workspace_slug}/notebooks",
        headers=headers,
        json={"name": "My Research Notes", "description": "Test notebook"},
    )
    assert notebook_response.status_code == 200
    notebook = notebook_response.json()

    # Verify notebook has slug
    assert "slug" in notebook
    assert notebook["slug"] == "my-research-notes"
    assert notebook["name"] == "My Research Notes"
    assert notebook["description"] == "Test notebook"


def test_nested_notebook_get_by_slug(test_client, auth_headers):
    """Test getting a notebook by slug using nested URL structure."""
    headers = auth_headers[0]

    # Create workspace
    workspace_response = test_client.post(
        "/api/v1/workspaces/",
        headers=headers,
        json={"name": "Get Notebook Workspace"},
    )
    workspace_slug = workspace_response.json()["slug"]

    # Create notebook
    notebook_response = test_client.post(
        f"/api/v1/workspaces/{workspace_slug}/notebooks",
        headers=headers,
        json={"name": "Test Notebook", "description": "For retrieval test"},
    )
    notebook = notebook_response.json()
    notebook_slug = notebook["slug"]
    notebook_id = notebook["id"]

    # Get notebook by slug
    get_by_slug_response = test_client.get(
        f"/api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}",
        headers=headers,
    )
    assert get_by_slug_response.status_code == 200
    retrieved = get_by_slug_response.json()
    assert retrieved["id"] == notebook_id
    assert retrieved["slug"] == notebook_slug
    assert retrieved["name"] == "Test Notebook"

    # Get notebook by ID (should still work)
    get_by_id_response = test_client.get(
        f"/api/v1/workspaces/{workspace_slug}/notebooks/{notebook_id}",
        headers=headers,
    )
    assert get_by_id_response.status_code == 200
    assert get_by_id_response.json()["id"] == notebook_id


def test_list_notebooks_nested(test_client, auth_headers):
    """Test listing notebooks using nested URL structure."""
    headers = auth_headers[0]

    # Create workspace
    workspace_response = test_client.post(
        "/api/v1/workspaces/",
        headers=headers,
        json={"name": "List Notebooks Workspace"},
    )
    workspace_slug = workspace_response.json()["slug"]

    # Create multiple notebooks
    for i in range(3):
        test_client.post(
            f"/api/v1/workspaces/{workspace_slug}/notebooks",
            headers=headers,
            json={"name": f"Notebook {i+1}", "description": f"Description {i+1}"},
        )

    # List notebooks
    list_response = test_client.get(
        f"/api/v1/workspaces/{workspace_slug}/notebooks",
        headers=headers,
    )
    assert list_response.status_code == 200
    notebooks = list_response.json()
    assert len(notebooks) == 3

    # Verify all notebooks have slugs
    for notebook in notebooks:
        assert "slug" in notebook
        assert "name" in notebook
        assert notebook["slug"].startswith("notebook-")
