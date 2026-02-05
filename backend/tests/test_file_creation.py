"""Tests for file creation with folder paths."""

from pathlib import Path


def test_create_file_with_folder_path(test_client, auth_headers, workspace_and_notebook):
    """Test creating a file with a folder path creates the folder structure."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Get notebook path on disk
    ws_detail = test_client.get(f"/api/v1/workspaces/{workspace['slug']}", headers=headers)
    notebook_path = Path(ws_detail.json()["path"]) / notebook["path"]

    # Create a file with a folder path using nested route
    file_path = "folder1/folder2/testfile.md"
    file_content = "# Test File\n\nThis is a test file in nested folders."

    file_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
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


def test_create_file_with_single_folder(test_client, auth_headers, workspace_and_notebook):
    """Test creating a file with a single folder path."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Get notebook path on disk
    ws_detail = test_client.get(f"/api/v1/workspaces/{workspace['slug']}", headers=headers)
    notebook_path = Path(ws_detail.json()["path"]) / notebook["path"]

    # Create a file with a single folder path using nested route
    file_path = "docs/readme.md"
    file_content = "# README\n\nDocumentation file."

    file_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
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
    full_file_path = notebook_path / file_path
    assert full_file_path.exists(), f"File does not exist at {full_file_path}"

    # Verify the folder exists
    docs_folder = notebook_path / "docs"
    assert docs_folder.exists() and docs_folder.is_dir(), f"Docs folder does not exist at {docs_folder}"


def test_create_file_without_folder(test_client, auth_headers, workspace_and_notebook):
    """Test creating a file without a folder path (in the root)."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Get notebook path on disk
    ws_detail = test_client.get(f"/api/v1/workspaces/{workspace['slug']}", headers=headers)
    notebook_path = Path(ws_detail.json()["path"]) / notebook["path"]

    # Create a file in the root (no folder) using nested route
    file_path = "notes.md"
    file_content = "# Notes\n\nJust some notes."

    file_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
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
    full_file_path = notebook_path / file_path
    assert full_file_path.exists(), f"File does not exist at {full_file_path}"
