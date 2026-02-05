"""Integration tests for folder API endpoints."""


def create_folder_with_files(test_client, headers, workspace, notebook, folder_path, num_files=3):
    """Helper to create a folder with files using nested routes."""
    for i in range(num_files):
        test_client.post(
            f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
            json={
                "path": f"{folder_path}/file_{i}.md",
                "content": f"# File {i}",
            },
            headers=headers,
        )


def test_get_root_folder(test_client, auth_headers, workspace_and_notebook):
    """Test getting the root folder of a notebook."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create some files in root
    for i in range(2):
        test_client.post(
            f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
            json={
                "path": f"root_file_{i}.md",
                "content": f"# Root File {i}",
            },
            headers=headers,
        )

    # Get root folder (empty path) using nested route
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/folders/",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == ""
    assert "files" in data
    assert "subfolders" in data
    assert "pagination" in data
    assert "workspace_slug" in data
    assert "notebook_slug" in data


def test_get_subfolder(test_client, auth_headers, workspace_and_notebook):
    """Test getting a subfolder with files."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create folder with files
    create_folder_with_files(test_client, headers, workspace, notebook, "docs", num_files=3)

    # Get folder using nested route
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/folders/docs",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "docs"
    assert data["name"] == "docs"
    assert len(data["files"]) == 3
    assert data["file_count"] == 3


def test_get_nested_folder(test_client, auth_headers, workspace_and_notebook):
    """Test getting a deeply nested folder."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create nested folder with files
    create_folder_with_files(test_client, headers, workspace, notebook, "level1/level2/level3", num_files=2)

    # Get nested folder using nested route
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/folders/level1/level2/level3",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "level1/level2/level3"
    assert data["name"] == "level3"
    assert len(data["files"]) == 2


def test_folder_with_subfolders(test_client, auth_headers, workspace_and_notebook):
    """Test getting a folder that contains subfolders."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create files in parent folder
    test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "parent/file.md",
            "content": "# Parent File",
        },
        headers=headers,
    )

    # Create files in subfolders
    test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "parent/child1/file.md",
            "content": "# Child 1 File",
        },
        headers=headers,
    )

    test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "parent/child2/file.md",
            "content": "# Child 2 File",
        },
        headers=headers,
    )

    # Get parent folder using nested route
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/folders/parent",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "parent"
    assert len(data["files"]) == 1  # Only files directly in parent
    assert len(data["subfolders"]) == 2
    subfolder_names = [sf["name"] for sf in data["subfolders"]]
    assert "child1" in subfolder_names
    assert "child2" in subfolder_names


def test_folder_pagination(test_client, auth_headers, workspace_and_notebook):
    """Test folder file listing with pagination."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create many files in a folder
    create_folder_with_files(test_client, headers, workspace, notebook, "many_files", num_files=10)

    # Get first page using nested route
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/folders/many_files?skip=0&limit=3",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["files"]) == 3
    assert data["pagination"]["total"] == 10
    assert data["pagination"]["has_more"] is True

    # Get second page using nested route
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/folders/many_files?skip=3&limit=3",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["files"]) == 3
    assert data["pagination"]["skip"] == 3


def test_update_folder_properties(test_client, auth_headers, workspace_and_notebook):
    """Test updating folder properties (metadata)."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create folder with a file
    test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "props_folder/file.md",
            "content": "# File",
        },
        headers=headers,
    )

    # Update folder properties using nested route
    response = test_client.put(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/folders/props_folder",
        json={
            "properties": {
                "title": "My Documentation",
                "description": "This folder contains documentation",
                "custom_field": "custom_value",
            }
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "My Documentation"
    assert data["description"] == "This folder contains documentation"
    assert data["properties"]["custom_field"] == "custom_value"

    # Verify properties persist
    get_response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/folders/props_folder",
        headers=headers,
    )
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["title"] == "My Documentation"
    assert get_data["properties"]["custom_field"] == "custom_value"


def test_delete_folder(test_client, auth_headers, workspace_and_notebook):
    """Test deleting a folder and all its contents."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create folder with files
    create_folder_with_files(test_client, headers, workspace, notebook, "to_delete", num_files=3)

    # Verify folder exists
    get_response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/folders/to_delete",
        headers=headers,
    )
    assert get_response.status_code == 200

    # Delete folder using nested route
    response = test_client.delete(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/folders/to_delete",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Folder deleted successfully"

    # Verify folder is deleted
    get_response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/folders/to_delete",
        headers=headers,
    )
    assert get_response.status_code == 404


def test_delete_nested_folder(test_client, auth_headers, workspace_and_notebook):
    """Test deleting a nested folder."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create nested structure
    test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "outer/inner/deep/file.md",
            "content": "# Deep File",
        },
        headers=headers,
    )

    # Delete inner folder using nested route
    response = test_client.delete(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/folders/outer/inner",
        headers=headers,
    )
    assert response.status_code == 200

    # Outer folder should still exist
    outer_response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/folders/outer",
        headers=headers,
    )
    assert outer_response.status_code == 200

    # Inner folder should be gone
    inner_response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/folders/outer/inner",
        headers=headers,
    )
    assert inner_response.status_code == 404


def test_delete_root_folder_fails(test_client, auth_headers, workspace_and_notebook):
    """Test that deleting the root folder is not allowed."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Try to delete root using nested route
    response = test_client.delete(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/folders/",
        headers=headers,
    )
    assert response.status_code == 400
    assert "Cannot delete root folder" in response.json()["detail"]


def test_get_nonexistent_folder(test_client, auth_headers, workspace_and_notebook):
    """Test getting a folder that doesn't exist."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/folders/nonexistent",
        headers=headers,
    )
    assert response.status_code == 404


def test_folder_requires_authentication(test_client):
    """Test that folder endpoints require authentication."""
    response = test_client.get("/api/v1/workspaces/test/notebooks/test/folders/test")
    assert response.status_code == 401

    response = test_client.put("/api/v1/workspaces/test/notebooks/test/folders/test", json={"properties": {}})
    assert response.status_code == 401

    response = test_client.delete("/api/v1/workspaces/test/notebooks/test/folders/test")
    assert response.status_code == 401


def test_folder_timestamps(test_client, auth_headers, workspace_and_notebook):
    """Test that folder response includes timestamps."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create folder
    test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "timed_folder/file.md",
            "content": "# File",
        },
        headers=headers,
    )

    # Get folder using nested route
    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/folders/timed_folder",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "created_at" in data
    assert "updated_at" in data
    assert data["created_at"] is not None
    assert data["updated_at"] is not None
