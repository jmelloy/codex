"""Tests for the event queue system."""

import json
import os
import time
from pathlib import Path

import pytest


def setup_test_user(test_client):
    """Register and login a test user."""
    username = f"test_queue_user_{int(time.time() * 1000)}"
    email = f"{username}@example.com"
    password = "testpass123"

    test_client.post("/api/v1/users/register", json={"username": username, "email": email, "password": password})
    login_response = test_client.post("/api/v1/users/token", data={"username": username, "password": password})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, username


def setup_workspace_and_notebook(test_client, headers, temp_workspace_dir):
    """Create a workspace and notebook for testing."""
    ws_response = test_client.post(
        "/api/v1/workspaces/",
        json={"name": "Test Queue Workspace"},
        headers=headers,
    )
    assert ws_response.status_code == 200
    workspace = ws_response.json()

    nb_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/",
        json={"name": "Test Queue Notebook"},
        headers=headers,
    )
    assert nb_response.status_code == 200
    notebook = nb_response.json()

    return workspace, notebook


def test_move_file_queued(test_client, temp_workspace_dir):
    """Test that move operations are queued."""
    from codex.core.queue_worker import EventQueueWorker
    from pathlib import Path
    
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Create a file
    create_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "test_move.md",
            "content": "# Test Content",
        },
        headers=headers,
    )
    assert create_response.status_code == 200
    file_id = create_response.json()["id"]
    
    # Get the notebook path
    workspace_path = Path(workspace["path"])
    notebook_path = workspace_path / notebook["path"]
    
    # Start a queue worker for this notebook
    worker = EventQueueWorker(str(notebook_path), notebook["id"], batch_interval=1.0)
    worker.start()

    try:
        # Move the file
        move_response = test_client.patch(
            f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/{file_id}/move",
            json={"new_path": "moved_file.md"},
            headers=headers,
        )
        assert move_response.status_code == 200
        data = move_response.json()

        # Verify the response indicates the operation was queued
        assert data["queued"] is True
        assert data["status"] == "pending"
        assert "queued successfully" in data["message"].lower()
        assert data["current_path"] == "test_move.md"
        assert data["target_path"] == "moved_file.md"
        assert "event_id" in data
        
        # Wait for the queue worker to process the event (up to 10 seconds)
        max_wait = 10
        start_time = time.time()
        file_exists = False
        
        moved_file_path = notebook_path / "moved_file.md"
        
        while time.time() - start_time < max_wait:
            if moved_file_path.exists():
                file_exists = True
                break
            time.sleep(0.5)
        
        assert file_exists, f"File was not moved within {max_wait} seconds"
        
        # Verify original file no longer exists
        original_path = notebook_path / "test_move.md"
        assert not original_path.exists(), "Original file still exists after move"
    
    finally:
        worker.stop(timeout=2.0)


def test_delete_file_queued(test_client, temp_workspace_dir):
    """Test that delete operations are queued."""
    from codex.core.queue_worker import EventQueueWorker
    from pathlib import Path
    
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Create a file
    create_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "test_delete.md",
            "content": "# Test Content",
        },
        headers=headers,
    )
    assert create_response.status_code == 200
    file_id = create_response.json()["id"]
    
    workspace_path = Path(workspace["path"])
    notebook_path = workspace_path / notebook["path"]
    file_path = notebook_path / "test_delete.md"
    
    # Wait a bit for the file to be created
    time.sleep(0.5)
    
    # Verify file was created
    assert file_path.exists()
    
    # Start a queue worker for this notebook
    worker = EventQueueWorker(str(notebook_path), notebook["id"], batch_interval=1.0)
    worker.start()

    try:
        # Delete the file
        delete_response = test_client.delete(
            f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/{file_id}",
            headers=headers,
        )
        assert delete_response.status_code == 200
        data = delete_response.json()
        
        # Verify the response indicates the operation was queued
        assert data["queued"] is True
        assert "queued successfully" in data["message"].lower()
        
        # Wait for the queue worker to process the event (up to 10 seconds)
        max_wait = 10
        start_time = time.time()
        file_deleted = False
        
        while time.time() - start_time < max_wait:
            if not file_path.exists():
                file_deleted = True
                break
            time.sleep(0.5)
        
        assert file_deleted, f"File was not deleted within {max_wait} seconds"
    
    finally:
        worker.stop(timeout=2.0)


def test_delete_folder_queued(test_client, temp_workspace_dir):
    """Test that folder delete operations are queued."""
    from codex.core.queue_worker import EventQueueWorker
    from pathlib import Path
    
    headers, _ = setup_test_user(test_client)
    workspace, notebook = setup_workspace_and_notebook(test_client, headers, temp_workspace_dir)

    # Create files in a folder
    test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "test_folder/file1.md",
            "content": "# File 1",
        },
        headers=headers,
    )
    test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
        json={
            "path": "test_folder/file2.md",
            "content": "# File 2",
        },
        headers=headers,
    )
    
    workspace_path = Path(workspace["path"])
    notebook_path = workspace_path / notebook["path"]
    folder_path = notebook_path / "test_folder"
    
    # Wait a bit for the files to be created
    time.sleep(0.5)
    
    # Verify folder was created with files
    assert folder_path.exists()
    assert (folder_path / "file1.md").exists()
    assert (folder_path / "file2.md").exists()
    
    # Start a queue worker for this notebook
    worker = EventQueueWorker(str(notebook_path), notebook["id"], batch_interval=1.0)
    worker.start()

    try:
        # Delete the folder
        delete_response = test_client.delete(
            f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/folders/test_folder",
            headers=headers,
        )
        assert delete_response.status_code == 200
        data = delete_response.json()
        
        # Verify the response indicates the operation was queued
        assert data["queued"] is True
        assert "queued successfully" in data["message"].lower()
        
        # Wait for the queue worker to process the event (up to 10 seconds)
        max_wait = 10
        start_time = time.time()
        folder_deleted = False
        
        while time.time() - start_time < max_wait:
            if not folder_path.exists():
                folder_deleted = True
                break
            time.sleep(0.5)
        
        assert folder_deleted, f"Folder was not deleted within {max_wait} seconds"
    
    finally:
        worker.stop(timeout=2.0)


def test_queue_event_model(temp_workspace_dir):
    """Test creating and querying FileSystemEvent model."""
    from codex.db.models import FileSystemEvent
    from codex.db.database import get_notebook_session
    from datetime import datetime, UTC
    from sqlmodel import select
    from pathlib import Path
    
    # Create a temporary notebook directory for testing
    test_notebook_path = Path(temp_workspace_dir) / "test_queue_notebook"
    test_notebook_path.mkdir(parents=True, exist_ok=True)
    
    # Create .codex directory
    codex_dir = test_notebook_path / ".codex"
    codex_dir.mkdir(exist_ok=True)
    
    # Initialize the notebook database
    from codex.db.database import init_notebook_db
    init_notebook_db(str(test_notebook_path))
    
    # Get a session
    session = get_notebook_session(str(test_notebook_path))
    
    try:
        # Create an event
        event = FileSystemEvent(
            notebook_id=1,
            event_type="move",
            file_path="test.md",
            new_path="renamed.md",
            status="pending"
        )
        session.add(event)
        session.commit()
        
        # Query the event
        result = session.execute(select(FileSystemEvent).where(FileSystemEvent.status == "pending"))
        queried_event = result.scalar_one()
        
        assert queried_event.event_type == "move"
        assert queried_event.file_path == "test.md"
        assert queried_event.new_path == "renamed.md"
        assert queried_event.status == "pending"
        assert queried_event.created_at is not None
        
    finally:
        session.close()


def test_queue_worker_processing(temp_workspace_dir):
    """Test that the queue worker processes events."""
    from codex.core.queue_worker import EventQueueWorker
    from codex.db.models import FileSystemEvent
    from codex.db.database import get_notebook_session, init_notebook_db
    from sqlmodel import select
    from pathlib import Path
    
    # Create a test notebook
    test_notebook_path = Path(temp_workspace_dir) / "test_worker_notebook"
    test_notebook_path.mkdir(parents=True, exist_ok=True)
    
    # Create .codex directory
    codex_dir = test_notebook_path / ".codex"
    codex_dir.mkdir(exist_ok=True)
    
    # Initialize the notebook database
    init_notebook_db(str(test_notebook_path))
    
    # Create a test file
    test_file = test_notebook_path / "test.md"
    test_file.write_text("# Test")
    
    # Add file metadata to database (simulating watcher indexing)
    from codex.core.watcher import NotebookFileHandler
    handler = NotebookFileHandler(str(test_notebook_path), 1)
    handler._update_file_metadata(str(test_file), "created")
    
    # Queue a move event
    session = get_notebook_session(str(test_notebook_path))
    try:
        event = FileSystemEvent(
            notebook_id=1,
            event_type="move",
            file_path="test.md",
            new_path="renamed.md",
            status="pending"
        )
        session.add(event)
        session.commit()
        event_id = event.id  # Store the ID before closing the session
    finally:
        session.close()
    
    # Start the worker with a short interval
    worker = EventQueueWorker(str(test_notebook_path), 1, batch_interval=1.0)
    worker.start()
    
    try:
        # Wait for the worker to process the event
        max_wait = 5
        start_time = time.time()
        event_processed = False
        
        while time.time() - start_time < max_wait:
            session = get_notebook_session(str(test_notebook_path))
            try:
                result = session.execute(
                    select(FileSystemEvent).where(FileSystemEvent.id == event_id)
                )
                processed_event = result.scalar_one_or_none()
                if processed_event and processed_event.status == "completed":
                    event_processed = True
                    break
            finally:
                session.close()
            time.sleep(0.5)
        
        assert event_processed, f"Event was not processed within {max_wait} seconds"
        
        # Verify the file was actually moved
        assert not test_file.exists(), "Original file still exists"
        assert (test_notebook_path / "renamed.md").exists(), "Renamed file doesn't exist"
        
    finally:
        worker.stop(timeout=2.0)
