"""Tests for file creation with folder paths."""

import os
import tempfile
from pathlib import Path


def test_create_file_with_folder_path(test_client, temp_workspace_dir):
    """Test creating a file with a folder path creates the folder structure."""
    # Login
    test_client.post(
        "/api/register",
        json={"username": "testuser_file", "email": "testfile@example.com", "password": "testpass123"},
    )

    login_response = test_client.post("/api/token", data={"username": "testuser_file", "password": "testpass123"})
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a workspace
    workspace_response = test_client.post(
        "/api/v1/workspaces/", json={"name": "Test Workspace", "path": temp_workspace_dir}, headers=headers
    )
    assert workspace_response.status_code == 200
    workspace_data = workspace_response.json()
    workspace_id = workspace_data["id"]
    # Use the actual workspace path returned by the API (not temp_workspace_dir)
    actual_workspace_path = Path(workspace_data["path"])

    # Create a notebook
    notebook_response = test_client.post(
        "/api/v1/notebooks/", json={"name": "Test Notebook", "workspace_id": workspace_id}, headers=headers
    )
    assert notebook_response.status_code == 200
    notebook_data = notebook_response.json()
    notebook_id = notebook_data["id"]

    # Create a file with a folder path
    file_path = "folder1/folder2/testfile.md"
    file_content = "# Test File\n\nThis is a test file in nested folders."

    file_response = test_client.post(
        "/api/v1/files/",
        json={
            "notebook_id": notebook_id,
            "workspace_id": workspace_id,
            "path": file_path,
            "content": file_content,
        },
        headers=headers,
    )

    # Check that the file was created successfully
    assert file_response.status_code == 200, f"Failed to create file: {file_response.json()}"
    file_data = file_response.json()
    assert file_data["path"] == file_path
    assert file_data["filename"] == "testfile.md"

    # Verify that the folder structure was created on disk
    # Use the actual workspace path and notebook.path from the API responses
    notebook_path = actual_workspace_path / notebook_data["path"]
    full_file_path = notebook_path / file_path
    assert full_file_path.exists(), f"File does not exist at {full_file_path}"

    # Verify the folder structure exists
    folder1 = notebook_path / "folder1"
    folder2 = notebook_path / "folder1" / "folder2"
    assert folder1.exists() and folder1.is_dir(), f"Folder1 does not exist at {folder1}"
    assert folder2.exists() and folder2.is_dir(), f"Folder2 does not exist at {folder2}"

    # Verify the file content
    with open(full_file_path, "r") as f:
        content = f.read()
    assert content == file_content


def test_create_file_with_single_folder(test_client, temp_workspace_dir):
    """Test creating a file with a single folder path."""
    # Login
    test_client.post(
        "/api/register",
        json={"username": "testuser_single", "email": "testsingle@example.com", "password": "testpass123"},
    )

    login_response = test_client.post("/api/token", data={"username": "testuser_single", "password": "testpass123"})
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a workspace
    workspace_response = test_client.post(
        "/api/v1/workspaces/", json={"name": "Test Workspace 2", "path": temp_workspace_dir}, headers=headers
    )
    assert workspace_response.status_code == 200
    workspace_data = workspace_response.json()
    workspace_id = workspace_data["id"]
    # Use the actual workspace path returned by the API
    actual_workspace_path = Path(workspace_data["path"])

    # Create a notebook
    notebook_response = test_client.post(
        "/api/v1/notebooks/", json={"name": "Test Notebook 2", "workspace_id": workspace_id}, headers=headers
    )
    assert notebook_response.status_code == 200
    notebook_data = notebook_response.json()
    notebook_id = notebook_data["id"]

    # Create a file with a single folder path
    file_path = "docs/readme.md"
    file_content = "# README\n\nDocumentation file."

    file_response = test_client.post(
        "/api/v1/files/",
        json={
            "notebook_id": notebook_id,
            "workspace_id": workspace_id,
            "path": file_path,
            "content": file_content,
        },
        headers=headers,
    )

    # Check that the file was created successfully
    assert file_response.status_code == 200, f"Failed to create file: {file_response.json()}"
    file_data = file_response.json()
    assert file_data["path"] == file_path
    assert file_data["filename"] == "readme.md"

    # Verify that the folder was created on disk
    # Use the actual workspace path and notebook.path from the API responses
    notebook_path = actual_workspace_path / notebook_data["path"]
    full_file_path = notebook_path / file_path
    assert full_file_path.exists(), f"File does not exist at {full_file_path}"

    # Verify the folder exists
    docs_folder = notebook_path / "docs"
    assert docs_folder.exists() and docs_folder.is_dir(), f"Docs folder does not exist at {docs_folder}"


def test_create_file_without_folder(test_client, temp_workspace_dir):
    """Test creating a file without a folder path (in the root)."""
    # Login
    test_client.post(
        "/api/register",
        json={"username": "testuser_root", "email": "testroot@example.com", "password": "testpass123"},
    )

    login_response = test_client.post("/api/token", data={"username": "testuser_root", "password": "testpass123"})
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a workspace
    workspace_response = test_client.post(
        "/api/v1/workspaces/", json={"name": "Test Workspace 3", "path": temp_workspace_dir}, headers=headers
    )
    assert workspace_response.status_code == 200
    workspace_data = workspace_response.json()
    workspace_id = workspace_data["id"]
    # Use the actual workspace path returned by the API
    actual_workspace_path = Path(workspace_data["path"])

    # Create a notebook
    notebook_response = test_client.post(
        "/api/v1/notebooks/", json={"name": "Test Notebook 3", "workspace_id": workspace_id}, headers=headers
    )
    assert notebook_response.status_code == 200
    notebook_data = notebook_response.json()
    notebook_id = notebook_data["id"]

    # Create a file in the root (no folder)
    file_path = "notes.md"
    file_content = "# Notes\n\nJust some notes."

    file_response = test_client.post(
        "/api/v1/files/",
        json={
            "notebook_id": notebook_id,
            "workspace_id": workspace_id,
            "path": file_path,
            "content": file_content,
        },
        headers=headers,
    )

    # Check that the file was created successfully
    assert file_response.status_code == 200, f"Failed to create file: {file_response.json()}"
    file_data = file_response.json()
    assert file_data["path"] == file_path
    assert file_data["filename"] == "notes.md"

    # Verify that the file exists on disk
    # Use the actual workspace path and notebook.path from the API responses
    notebook_path = actual_workspace_path / notebook_data["path"]
    full_file_path = notebook_path / file_path
    assert full_file_path.exists(), f"File does not exist at {full_file_path}"
