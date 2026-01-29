"""Tests for image metadata extraction in the file watcher."""

import json
import os
import tempfile
from pathlib import Path

import pytest
from PIL import Image
from sqlmodel import Session, select

from codex.core.watcher import NotebookFileHandler
from codex.db.database import get_notebook_session, init_notebook_db
from codex.db.models import FileMetadata


@pytest.fixture
def temp_notebook():
    """Create a temporary directory for notebook tests."""
    temp_dir = tempfile.mkdtemp()
    
    # Initialize the notebook database
    init_notebook_db(temp_dir)
    
    yield temp_dir
    
    # Cleanup
    import shutil
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass


def test_watcher_extracts_image_metadata(temp_notebook):
    """Test that the watcher extracts image metadata when scanning files."""
    # Create a test image
    img_path = os.path.join(temp_notebook, "test_photo.png")
    img = Image.new("RGB", (1024, 768), color="blue")
    img.save(img_path, format="PNG")
    
    # Create a file handler
    handler = NotebookFileHandler(temp_notebook, notebook_id=1)
    
    # Trigger the file metadata update
    handler._update_file_metadata(img_path, "created")
    
    # Query the database to verify metadata was stored
    session = get_notebook_session(temp_notebook)
    try:
        result = session.execute(
            select(FileMetadata).where(
                FileMetadata.notebook_id == 1,
                FileMetadata.filename == "test_photo.png"
            )
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
    # Create a test JPEG image
    img_path = os.path.join(temp_notebook, "photo.jpg")
    img = Image.new("RGB", (640, 480), color="red")
    img.save(img_path, format="JPEG")
    
    # Create a file handler
    handler = NotebookFileHandler(temp_notebook, notebook_id=1)
    
    # Trigger the file metadata update
    handler._update_file_metadata(img_path, "created")
    
    # Query the database to verify metadata was stored
    session = get_notebook_session(temp_notebook)
    try:
        result = session.execute(
            select(FileMetadata).where(
                FileMetadata.notebook_id == 1,
                FileMetadata.filename == "photo.jpg"
            )
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
    # Create a test image with alpha channel
    img_path = os.path.join(temp_notebook, "transparent.png")
    img = Image.new("RGBA", (500, 300), color=(0, 255, 0, 128))
    img.save(img_path, format="PNG")
    
    # Create a file handler
    handler = NotebookFileHandler(temp_notebook, notebook_id=1)
    
    # Trigger the file metadata update
    handler._update_file_metadata(img_path, "created")
    
    # Query the database to verify metadata was stored
    session = get_notebook_session(temp_notebook)
    try:
        result = session.execute(
            select(FileMetadata).where(
                FileMetadata.notebook_id == 1,
                FileMetadata.filename == "transparent.png"
            )
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
    # Create a text file
    text_path = os.path.join(temp_notebook, "document.txt")
    with open(text_path, "w") as f:
        f.write("This is just text content")
    
    # Create a file handler
    handler = NotebookFileHandler(temp_notebook, notebook_id=1)
    
    # Trigger the file metadata update
    handler._update_file_metadata(text_path, "created")
    
    # Query the database to verify metadata was stored
    session = get_notebook_session(temp_notebook)
    try:
        result = session.execute(
            select(FileMetadata).where(
                FileMetadata.notebook_id == 1,
                FileMetadata.filename == "document.txt"
            )
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
    # Create a test image
    img_path = os.path.join(temp_notebook, "artwork.png")
    img = Image.new("RGB", (800, 600), color="purple")
    img.save(img_path, format="PNG")
    
    # Create a sidecar file with additional metadata
    sidecar_path = os.path.join(temp_notebook, "artwork.png.json")
    with open(sidecar_path, "w") as f:
        json.dump({
            "title": "My Artwork",
            "description": "A beautiful piece of digital art",
            "artist": "Test Artist"
        }, f)
    
    # Create a file handler
    handler = NotebookFileHandler(temp_notebook, notebook_id=1)
    
    # Trigger the file metadata update
    handler._update_file_metadata(img_path, "created")
    
    # Query the database to verify metadata was stored
    session = get_notebook_session(temp_notebook)
    try:
        result = session.execute(
            select(FileMetadata).where(
                FileMetadata.notebook_id == 1,
                FileMetadata.filename == "artwork.png"
            )
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
