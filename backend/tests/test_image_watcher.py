"""Tests for image metadata extraction in the file watcher."""

import json
import os
import tempfile
import uuid

import pytest
from PIL import Image
from sqlmodel import select

from codex.core.watcher import NotebookFileHandler, NotebookWatcher, get_watcher_for_notebook
from codex.db.database import get_notebook_session, init_notebook_db
from codex.db.models import FileMetadata


@pytest.fixture
def temp_notebook():
    """Create a temporary directory for notebook tests.

    Only starts the queue processor (no filesystem observer or background
    indexing) so that tests can control exactly which operations are
    processed via enqueue_operation(..., wait=True).
    """
    temp_dir = tempfile.mkdtemp()

    # Initialize the notebook database (applies migrations including unique constraint)
    init_notebook_db(temp_dir)

    watcher = NotebookWatcher(temp_dir, notebook_id=1)
    watcher.queue.BATCH_INTERVAL = 0.1  # Speed up tests
    # Only start the queue processor, not the observer or background indexing
    watcher.queue.start()

    yield temp_dir, watcher

    # Cleanup - stop queue
    try:
        watcher.queue.stop(timeout=1.0)
    except Exception:
        pass

    import shutil

    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass


def test_watcher_extracts_image_metadata(temp_notebook):
    """Test that the watcher extracts image metadata when scanning files."""
    temp_dir, watcher = temp_notebook
    # Create a test image
    photo_name = f"{uuid.uuid4()}.png"
    img_path = os.path.join(temp_dir, photo_name)
    img = Image.new("RGB", (1024, 768), color="blue")
    img.save(img_path, format="PNG")

    # Wait for watcher to process (synchronously)
    watcher.enqueue_operation(img_path, None, "created", wait=True)

    # Query the database to verify metadata was stored
    rel_path = os.path.relpath(img_path, temp_dir)
    session = get_notebook_session(temp_dir)
    try:
        result = session.execute(
            select(FileMetadata).where(FileMetadata.notebook_id == 1, FileMetadata.path == rel_path)
        )
        file_meta = result.scalar_one_or_none()

        assert file_meta is not None
        assert file_meta.content_type == "image/png"

        # Check that properties contains image metadata
        properties = json.loads(file_meta.properties)
        assert "width" in properties
        assert "height" in properties
        assert "format" in properties
        assert "mode" in properties

        assert properties["width"] == 1024
        assert properties["height"] == 768
        assert properties["format"] == "PNG"
        assert properties["mode"] == "RGB"
    finally:
        session.close()


def test_watcher_extracts_jpeg_metadata(temp_notebook):
    """Test that the watcher extracts JPEG image metadata."""
    temp_dir, watcher = temp_notebook
    # Create a test JPEG image
    photo_name = f"{uuid.uuid4()}.jpg"
    img_path = os.path.join(temp_dir, photo_name)
    img = Image.new("RGB", (640, 480), color="red")
    img.save(img_path, format="JPEG")

    # Wait for watcher to process (synchronously)
    watcher.enqueue_operation(img_path, None, "created", wait=True)
    # Query the database to verify metadata was stored
    rel_path = os.path.relpath(img_path, temp_dir)
    session = get_notebook_session(temp_dir)
    try:
        result = session.execute(
            select(FileMetadata).where(FileMetadata.notebook_id == 1, FileMetadata.path == rel_path)
        )
        file_meta = result.scalar_one_or_none()

        assert file_meta is not None
        assert file_meta.content_type == "image/jpeg"

        # Check that properties contains image metadata
        properties = json.loads(file_meta.properties)
        assert properties["width"] == 640
        assert properties["height"] == 480
        assert properties["format"] == "JPEG"
        assert properties["mode"] == "RGB"
    finally:
        session.close()


def test_watcher_extracts_rgba_image_metadata(temp_notebook):
    """Test that the watcher extracts metadata from images with alpha channel."""
    temp_dir, watcher = temp_notebook
    # Create a test image with alpha channel
    photo_name = f"{uuid.uuid4()}.png"
    img_path = os.path.join(temp_dir, photo_name)
    img = Image.new("RGBA", (500, 300), color=(0, 255, 0, 128))
    img.save(img_path, format="PNG")

    # Wait for watcher to process (synchronously)
    watcher.enqueue_operation(img_path, None, "created", wait=True)

    # Query the database to verify metadata was stored
    rel_path = os.path.relpath(img_path, temp_dir)
    session = get_notebook_session(temp_dir)
    try:
        result = session.execute(
            select(FileMetadata).where(FileMetadata.notebook_id == 1, FileMetadata.path == rel_path)
        )
        file_meta = result.scalar_one_or_none()

        assert file_meta is not None

        # Check that properties contains image metadata including mode
        properties = json.loads(file_meta.properties)
        assert properties["width"] == 500
        assert properties["height"] == 300
        assert properties["mode"] == "RGBA"
    finally:
        session.close()


def test_watcher_non_image_no_image_metadata(temp_notebook):
    """Test that non-image files don't have image metadata."""
    temp_dir, watcher = temp_notebook
    # Create a text file
    text_path = os.path.join(temp_dir, "document.txt")
    with open(text_path, "w") as f:
        f.write("This is just text content")

    # Wait for watcher to process (synchronously)
    watcher.enqueue_operation(text_path, None, "created", wait=True)

    # Query the database to verify metadata was stored
    rel_path = os.path.relpath(text_path, temp_dir)
    session = get_notebook_session(temp_dir)
    try:
        result = session.execute(
            select(FileMetadata).where(FileMetadata.notebook_id == 1, FileMetadata.path == rel_path)
        )
        file_meta = result.scalar_one_or_none()

        assert file_meta is not None
        assert file_meta.content_type == "text/plain"

        # Properties should exist but not have image metadata
        properties = json.loads(file_meta.properties)
        assert "width" not in properties
        assert "height" not in properties
        assert "format" not in properties
    finally:
        session.close()


def test_watcher_image_with_sidecar_metadata(temp_notebook):
    """Test that image metadata is combined with sidecar metadata."""
    temp_dir, watcher = temp_notebook
    # Create a test image
    img_path = os.path.join(temp_dir, "artwork.png")
    img = Image.new("RGB", (800, 600), color="purple")
    img.save(img_path, format="PNG")

    # Create a sidecar file with additional metadata
    sidecar_path = os.path.join(temp_dir, "artwork.png.json")
    with open(sidecar_path, "w") as f:
        json.dump(
            {"title": "My Artwork", "description": "A beautiful piece of digital art", "artist": "Test Artist"}, f
        )

    # Wait for watcher to process (synchronously)
    watcher.enqueue_operation(img_path, sidecar_path, "created", wait=True)
    # Query the database to verify metadata was stored
    rel_path = os.path.relpath(img_path, temp_dir)
    session = get_notebook_session(temp_dir)
    try:
        result = session.execute(
            select(FileMetadata).where(FileMetadata.notebook_id == 1, FileMetadata.path == rel_path)
        )
        file_meta = result.scalar_one_or_none()

        assert file_meta is not None

        # Check that both image metadata and sidecar metadata are present
        properties = json.loads(file_meta.properties)

        # Image metadata
        assert properties["width"] == 800
        assert properties["height"] == 600
        assert properties["format"] == "PNG"
        assert properties["mode"] == "RGB"

        # Sidecar metadata
        assert properties["title"] == "My Artwork"
        assert properties["description"] == "A beautiful piece of digital art"
        assert properties["artist"] == "Test Artist"

        # Check indexed fields
        assert file_meta.title == "My Artwork"
        assert file_meta.description == "A beautiful piece of digital art"
    finally:
        session.close()
