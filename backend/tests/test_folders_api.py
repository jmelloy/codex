"""Integration tests for folder API endpoints."""

import os
import time
from pathlib import Path


def setup_test_user(test_client):
    """Register and login a test user."""
    username = f"test_folders_user_{int(time.time() * 1000)}"
    email = f"{username}@example.com"
    password = "testpass123"

    test_client.post("/api/register", json={"username": username, "email": email, "password": password})
    login_response = test_client.post("/api/token", data={"username": username, "password": password})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, username


def setup_workspace_and_notebook(test_client, headers, temp_workspace_dir):
    """Create a workspace and notebook for testing."""
    # Create workspace
    ws_response = test_client.post(
        "/api/v1/workspaces/",
        json={"name": "Test Folders Workspace", "path": temp_workspace_dir},
        headers=headers,
    )
    assert ws_response.status_code == 200
    workspace = ws_response.json()

    # Create notebook
    nb_response = test_client.post(
        "/api/v1/notebooks/",
        json={"workspace_id": workspace["id"], "name": "Test Notebook"},
        headers=headers,
    )
    assert nb_response.status_code == 200
    notebook = nb_response.json()

    return workspace, notebook


def create_folder_with_files(test_client, headers, workspace, notebook, folder_path, num_files=3):
    """Helper to create a folder with files."""
    for i in range(num_files):
        test_client.post(
            "/api/v1/files/",
            json={
                "notebook_id": notebook["id"],
                "workspace_id": workspace["id"],
                "path": f"{folder_path}/file_{i}.md",
                "content": f"# File {i}",
            },
            headers=headers,
        )


def test_get_root_folder(test_client, temp_workspace_dir):
    """Test getting the root folder of a notebook."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Create some files in root
    for i in range(2):
        test_client.post(
            "/api/v1/files/",
            json={
                "notebook_id": notebook["id"],
                "workspace_id": workspace["id"],
                "path": f"root_file_{i}.md",
                "content": f"# Root File {i}",
            },
            headers=headers,
        )

    # Get root folder (empty path)
    response = test_client.get(
        f"/api/v1/folders/?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == ""
    assert "files" in data
    assert "subfolders" in data
    assert "pagination" in data


def test_get_subfolder(test_client, temp_workspace_dir):
    """Test getting a subfolder with files."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Create folder with files
    create_folder_with_files(test_client, headers, workspace, notebook, "docs", num_files=3)

    # Get folder
    response = test_client.get(
        f"/api/v1/folders/docs?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "docs"
    assert data["name"] == "docs"
    assert len(data["files"]) == 3
    assert data["file_count"] == 3


def test_get_nested_folder(test_client, temp_workspace_dir):
    """Test getting a deeply nested folder."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Create nested folder with files
    create_folder_with_files(test_client, headers, workspace, notebook, "level1/level2/level3", num_files=2)

    # Get nested folder
    response = test_client.get(
        f"/api/v1/folders/level1/level2/level3?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "level1/level2/level3"
    assert data["name"] == "level3"
    assert len(data["files"]) == 2


def test_folder_with_subfolders(test_client, temp_workspace_dir):
    """Test getting a folder that contains subfolders."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Create files in parent folder
    test_client.post(
        "/api/v1/files/",
        json={
            "notebook_id": notebook["id"],
            "workspace_id": workspace["id"],
            "path": "parent/file.md",
            "content": "# Parent File",
        },
        headers=headers,
    )

    # Create files in subfolders
    test_client.post(
        "/api/v1/files/",
        json={
            "notebook_id": notebook["id"],
            "workspace_id": workspace["id"],
            "path": "parent/child1/file.md",
            "content": "# Child 1 File",
        },
        headers=headers,
    )

    test_client.post(
        "/api/v1/files/",
        json={
            "notebook_id": notebook["id"],
            "workspace_id": workspace["id"],
            "path": "parent/child2/file.md",
            "content": "# Child 2 File",
        },
        headers=headers,
    )

    # Get parent folder
    response = test_client.get(
        f"/api/v1/folders/parent?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
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


def test_folder_pagination(test_client, temp_workspace_dir):
    """Test folder file listing with pagination."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Create many files in a folder
    create_folder_with_files(test_client, headers, workspace, notebook, "many_files", num_files=10)

    # Get first page
    response = test_client.get(
        f"/api/v1/folders/many_files?notebook_id={notebook['id']}&workspace_id={workspace['id']}&skip=0&limit=3",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["files"]) == 3
    assert data["pagination"]["total"] == 10
    assert data["pagination"]["has_more"] is True

    # Get second page
    response = test_client.get(
        f"/api/v1/folders/many_files?notebook_id={notebook['id']}&workspace_id={workspace['id']}&skip=3&limit=3",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["files"]) == 3
    assert data["pagination"]["skip"] == 3


def test_update_folder_properties(test_client, temp_workspace_dir):
    """Test updating folder properties (metadata)."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Create folder with a file
    test_client.post(
        "/api/v1/files/",
        json={
            "notebook_id": notebook["id"],
            "workspace_id": workspace["id"],
            "path": "props_folder/file.md",
            "content": "# File",
        },
        headers=headers,
    )

    # Update folder properties
    response = test_client.put(
        f"/api/v1/folders/props_folder?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
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
        f"/api/v1/folders/props_folder?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        headers=headers,
    )
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["title"] == "My Documentation"
    assert get_data["properties"]["custom_field"] == "custom_value"


def test_delete_folder(test_client, temp_workspace_dir):
    """Test deleting a folder and all its contents."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Create folder with files
    create_folder_with_files(test_client, headers, workspace, notebook, "to_delete", num_files=3)

    # Verify folder exists
    get_response = test_client.get(
        f"/api/v1/folders/to_delete?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        headers=headers,
    )
    assert get_response.status_code == 200

    # Delete folder
    response = test_client.delete(
        f"/api/v1/folders/to_delete?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Folder deleted successfully"

    # Verify folder is deleted
    get_response = test_client.get(
        f"/api/v1/folders/to_delete?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        headers=headers,
    )
    assert get_response.status_code == 404


def test_delete_nested_folder(test_client, temp_workspace_dir):
    """Test deleting a nested folder."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Create nested structure
    test_client.post(
        "/api/v1/files/",
        json={
            "notebook_id": notebook["id"],
            "workspace_id": workspace["id"],
            "path": "outer/inner/deep/file.md",
            "content": "# Deep File",
        },
        headers=headers,
    )

    # Delete inner folder
    response = test_client.delete(
        f"/api/v1/folders/outer/inner?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        headers=headers,
    )
    assert response.status_code == 200

    # Outer folder should still exist
    outer_response = test_client.get(
        f"/api/v1/folders/outer?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        headers=headers,
    )
    assert outer_response.status_code == 200

    # Inner folder should be gone
    inner_response = test_client.get(
        f"/api/v1/folders/outer/inner?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        headers=headers,
    )
    assert inner_response.status_code == 404


def test_delete_root_folder_fails(test_client, temp_workspace_dir):
    """Test that deleting the root folder is not allowed."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Try to delete root
    response = test_client.delete(
        f"/api/v1/folders/?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        headers=headers,
    )
    assert response.status_code == 400
    assert "Cannot delete root folder" in response.json()["detail"]


def test_get_nonexistent_folder(test_client, temp_workspace_dir):
    """Test getting a folder that doesn't exist."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    response = test_client.get(
        f"/api/v1/folders/nonexistent?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        headers=headers,
    )
    assert response.status_code == 404


def test_folder_requires_authentication(test_client):
    """Test that folder endpoints require authentication."""
    response = test_client.get("/api/v1/folders/test?notebook_id=1&workspace_id=1")
    assert response.status_code == 401

    response = test_client.put("/api/v1/folders/test?notebook_id=1&workspace_id=1", json={"properties": {}})
    assert response.status_code == 401

    response = test_client.delete("/api/v1/folders/test?notebook_id=1&workspace_id=1")
    assert response.status_code == 401


def test_folder_timestamps(test_client, temp_workspace_dir):
    """Test that folder response includes timestamps."""
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Create folder
    test_client.post(
        "/api/v1/files/",
        json={
            "notebook_id": notebook["id"],
            "workspace_id": workspace["id"],
            "path": "timed_folder/file.md",
            "content": "# File",
        },
        headers=headers,
    )

    # Get folder
    response = test_client.get(
        f"/api/v1/folders/timed_folder?notebook_id={notebook['id']}&workspace_id={workspace['id']}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "created_at" in data
    assert "updated_at" in data
    assert data["created_at"] is not None
    assert data["updated_at"] is not None
