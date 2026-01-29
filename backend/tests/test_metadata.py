"""Tests for metadata parsing functionality."""

import tempfile
from pathlib import Path

import pytest

from codex.core.metadata import MetadataParser


class TestResolveSidecar:
    """Tests for MetadataParser.resolve_sidecar function."""

    def test_no_sidecar_exists(self, tmp_path):
        """Test when no sidecar file exists."""
        # Create a main file without any sidecar
        main_file = tmp_path / "document.txt"
        main_file.write_text("content")
        
        filepath, sidecar = MetadataParser.resolve_sidecar(str(main_file))
        
        assert filepath == str(main_file)
        assert sidecar is None

    def test_json_sidecar_exists(self, tmp_path):
        """Test when a .json sidecar exists."""
        main_file = tmp_path / "document.txt"
        sidecar_file = tmp_path / "document.txt.json"
        
        main_file.write_text("content")
        sidecar_file.write_text('{"key": "value"}')
        
        filepath, sidecar = MetadataParser.resolve_sidecar(str(main_file))
        
        assert filepath == str(main_file)
        assert sidecar == str(sidecar_file)

    def test_xml_sidecar_exists(self, tmp_path):
        """Test when a .xml sidecar exists."""
        main_file = tmp_path / "document.txt"
        sidecar_file = tmp_path / "document.txt.xml"
        
        main_file.write_text("content")
        sidecar_file.write_text('<metadata></metadata>')
        
        filepath, sidecar = MetadataParser.resolve_sidecar(str(main_file))
        
        assert filepath == str(main_file)
        assert sidecar == str(sidecar_file)

    def test_md_sidecar_exists(self, tmp_path):
        """Test when a .md sidecar exists."""
        main_file = tmp_path / "document.txt"
        sidecar_file = tmp_path / "document.txt.md"
        
        main_file.write_text("content")
        sidecar_file.write_text('---\ntitle: test\n---\ncontent')
        
        filepath, sidecar = MetadataParser.resolve_sidecar(str(main_file))
        
        assert filepath == str(main_file)
        assert sidecar == str(sidecar_file)

    def test_dot_prefixed_json_sidecar(self, tmp_path):
        """Test when a dot-prefixed .json sidecar exists."""
        main_file = tmp_path / "document.txt"
        sidecar_file = tmp_path / ".document.txt.json"
        
        main_file.write_text("content")
        sidecar_file.write_text('{"key": "value"}')
        
        filepath, sidecar = MetadataParser.resolve_sidecar(str(main_file))
        
        assert filepath == str(main_file)
        assert sidecar == str(sidecar_file)

    def test_dot_prefixed_md_sidecar(self, tmp_path):
        """Test when a dot-prefixed .md sidecar exists."""
        main_file = tmp_path / "document.txt"
        sidecar_file = tmp_path / ".document.txt.md"
        
        main_file.write_text("content")
        sidecar_file.write_text('---\ntitle: test\n---\ncontent')
        
        filepath, sidecar = MetadataParser.resolve_sidecar(str(main_file))
        
        assert filepath == str(main_file)
        assert sidecar == str(sidecar_file)

    def test_passed_in_regular_sidecar_json(self, tmp_path):
        """Test when passing in the sidecar file itself (regular .json)."""
        main_file = tmp_path / "document.txt"
        sidecar_file = tmp_path / "document.txt.json"
        
        main_file.write_text("content")
        sidecar_file.write_text('{"key": "value"}')
        
        filepath, sidecar = MetadataParser.resolve_sidecar(str(sidecar_file))
        
        assert filepath == str(main_file)
        assert sidecar == str(sidecar_file)

    def test_passed_in_regular_sidecar_md(self, tmp_path):
        """Test when passing in the sidecar file itself (regular .md)."""
        main_file = tmp_path / "document.txt"
        sidecar_file = tmp_path / "document.txt.md"
        
        main_file.write_text("content")
        sidecar_file.write_text('---\ntitle: test\n---\ncontent')
        
        filepath, sidecar = MetadataParser.resolve_sidecar(str(sidecar_file))
        
        assert filepath == str(main_file)
        assert sidecar == str(sidecar_file)

    def test_passed_in_dot_prefixed_sidecar_json(self, tmp_path):
        """Test when passing in a dot-prefixed sidecar file."""
        main_file = tmp_path / "document.txt"
        sidecar_file = tmp_path / ".document.txt.json"
        
        main_file.write_text("content")
        sidecar_file.write_text('{"key": "value"}')
        
        filepath, sidecar = MetadataParser.resolve_sidecar(str(sidecar_file))
        
        assert filepath == str(main_file)
        assert sidecar == str(sidecar_file)

    def test_passed_in_dot_prefixed_sidecar_md(self, tmp_path):
        """Test when passing in a dot-prefixed markdown sidecar file."""
        main_file = tmp_path / "document.txt"
        sidecar_file = tmp_path / ".document.txt.md"
        
        main_file.write_text("content")
        sidecar_file.write_text('---\ntitle: test\n---\ncontent')
        
        filepath, sidecar = MetadataParser.resolve_sidecar(str(sidecar_file))
        
        assert filepath == str(main_file)
        assert sidecar == str(sidecar_file)

    def test_priority_order_regular_before_dot(self, tmp_path):
        """Test that regular sidecar is found before dot-prefixed when both exist."""
        main_file = tmp_path / "document.txt"
        regular_sidecar = tmp_path / "document.txt.json"
        dot_sidecar = tmp_path / ".document.txt.json"
        
        main_file.write_text("content")
        regular_sidecar.write_text('{"type": "regular"}')
        dot_sidecar.write_text('{"type": "dot"}')
        
        filepath, sidecar = MetadataParser.resolve_sidecar(str(main_file))
        
        assert filepath == str(main_file)
        assert sidecar == str(regular_sidecar)

    def test_priority_order_json_before_xml(self, tmp_path):
        """Test that .json sidecar is found before .xml when both exist."""
        main_file = tmp_path / "document.txt"
        json_sidecar = tmp_path / "document.txt.json"
        xml_sidecar = tmp_path / "document.txt.xml"
        
        main_file.write_text("content")
        json_sidecar.write_text('{"type": "json"}')
        xml_sidecar.write_text('<metadata><type>xml</type></metadata>')
        
        filepath, sidecar = MetadataParser.resolve_sidecar(str(main_file))
        
        assert filepath == str(main_file)
        assert sidecar == str(json_sidecar)

    def test_priority_order_xml_before_md(self, tmp_path):
        """Test that .xml sidecar is found before .md when both exist."""
        main_file = tmp_path / "document.txt"
        xml_sidecar = tmp_path / "document.txt.xml"
        md_sidecar = tmp_path / "document.txt.md"
        
        main_file.write_text("content")
        xml_sidecar.write_text('<metadata><type>xml</type></metadata>')
        md_sidecar.write_text('---\ntype: md\n---\ncontent')
        
        filepath, sidecar = MetadataParser.resolve_sidecar(str(main_file))
        
        assert filepath == str(main_file)
        assert sidecar == str(xml_sidecar)

    def test_nested_directory_structure(self, tmp_path):
        """Test sidecar resolution in nested directories."""
        nested_dir = tmp_path / "folder" / "subfolder"
        nested_dir.mkdir(parents=True)
        
        main_file = nested_dir / "document.txt"
        sidecar_file = nested_dir / "document.txt.json"
        
        main_file.write_text("content")
        sidecar_file.write_text('{"key": "value"}')
        
        filepath, sidecar = MetadataParser.resolve_sidecar(str(main_file))
        
        assert filepath == str(main_file)
        assert sidecar == str(sidecar_file)

    def test_nonexistent_main_file_with_sidecar(self, tmp_path):
        """Test when sidecar exists but main file doesn't (passed sidecar path)."""
        sidecar_file = tmp_path / "document.txt.json"
        sidecar_file.write_text('{"key": "value"}')
        
        filepath, sidecar = MetadataParser.resolve_sidecar(str(sidecar_file))
        
        # When passed a sidecar but main file doesn't exist, should return the original path and None
        assert filepath == str(sidecar_file)
        assert sidecar is None

    def test_nonexistent_main_file_with_dot_sidecar(self, tmp_path):
        """Test when dot-prefixed sidecar exists but main file doesn't."""
        sidecar_file = tmp_path / ".document.txt.json"
        sidecar_file.write_text('{"key": "value"}')
        
        filepath, sidecar = MetadataParser.resolve_sidecar(str(sidecar_file))
        
        # When passed a dot-prefixed sidecar but main file doesn't exist, returns the original path
        assert filepath == str(sidecar_file)
        assert sidecar is None

    def test_special_characters_in_filename(self, tmp_path):
        """Test with special characters in filename."""
        main_file = tmp_path / "document-with_special.chars.txt"
        sidecar_file = tmp_path / "document-with_special.chars.txt.json"
        
        main_file.write_text("content")
        sidecar_file.write_text('{"key": "value"}')
        
        filepath, sidecar = MetadataParser.resolve_sidecar(str(main_file))
        
        assert filepath == str(main_file)
        assert sidecar == str(sidecar_file)

    def test_file_with_multiple_dots(self, tmp_path):
        """Test with filename containing multiple dots."""
        main_file = tmp_path / "my.document.v2.txt"
        sidecar_file = tmp_path / "my.document.v2.txt.json"
        
        main_file.write_text("content")
        sidecar_file.write_text('{"key": "value"}')
        
        filepath, sidecar = MetadataParser.resolve_sidecar(str(main_file))
        
        assert filepath == str(main_file)
        assert sidecar == str(sidecar_file)

    def test_empty_filename(self, tmp_path):
        """Test with just extension (edge case)."""
        main_file = tmp_path / ".gitignore"
        sidecar_file = tmp_path / ".gitignore.json"
        
        main_file.write_text("content")
        sidecar_file.write_text('{"key": "value"}')
        
        filepath, sidecar = MetadataParser.resolve_sidecar(str(main_file))
        
        assert filepath == str(main_file)
        assert sidecar == str(sidecar_file)

    def test_xml_sidecar_with_dot_prefix(self, tmp_path):
        """Test dot-prefixed XML sidecar."""
        main_file = tmp_path / "document.txt"
        sidecar_file = tmp_path / ".document.txt.xml"
        
        main_file.write_text("content")
        sidecar_file.write_text('<metadata></metadata>')
        
        filepath, sidecar = MetadataParser.resolve_sidecar(str(main_file))
        
        assert filepath == str(main_file)
        assert sidecar == str(sidecar_file)

    def test_passed_in_xml_sidecar(self, tmp_path):
        """Test when passing in an XML sidecar directly."""
        main_file = tmp_path / "document.txt"
        sidecar_file = tmp_path / "document.txt.xml"
        
        main_file.write_text("content")
        sidecar_file.write_text('<metadata></metadata>')
        
        filepath, sidecar = MetadataParser.resolve_sidecar(str(sidecar_file))
        
        assert filepath == str(main_file)
        assert sidecar == str(sidecar_file)

    def test_absolute_vs_relative_paths(self, tmp_path):
        """Test that function works with absolute paths."""
        main_file = tmp_path / "document.txt"
        sidecar_file = tmp_path / "document.txt.json"
        
        main_file.write_text("content")
        sidecar_file.write_text('{"key": "value"}')
        
        # Use absolute path
        filepath, sidecar = MetadataParser.resolve_sidecar(str(main_file.absolute()))
        
        assert filepath == str(main_file.absolute())
        assert sidecar == str(sidecar_file.absolute())


class TestImageMetadata:
    """Tests for image metadata extraction."""

    def test_extract_png_metadata(self, tmp_path):
        """Test extracting metadata from a PNG image."""
        from PIL import Image
        
        # Create a simple test PNG image
        img_path = tmp_path / "test.png"
        img = Image.new("RGB", (100, 200), color="red")
        img.save(img_path, format="PNG")
        
        metadata = MetadataParser.extract_image_metadata(str(img_path))
        
        assert metadata is not None
        assert metadata["width"] == 100
        assert metadata["height"] == 200
        assert metadata["format"] == "PNG"
        assert metadata["mode"] == "RGB"

    def test_extract_jpeg_metadata(self, tmp_path):
        """Test extracting metadata from a JPEG image."""
        from PIL import Image
        
        # Create a simple test JPEG image
        img_path = tmp_path / "test.jpg"
        img = Image.new("RGB", (640, 480), color="blue")
        img.save(img_path, format="JPEG")
        
        metadata = MetadataParser.extract_image_metadata(str(img_path))
        
        assert metadata is not None
        assert metadata["width"] == 640
        assert metadata["height"] == 480
        assert metadata["format"] == "JPEG"
        assert metadata["mode"] == "RGB"

    def test_extract_rgba_image_metadata(self, tmp_path):
        """Test extracting metadata from an image with alpha channel."""
        from PIL import Image
        
        # Create a simple test image with alpha channel
        img_path = tmp_path / "test_alpha.png"
        img = Image.new("RGBA", (150, 150), color=(255, 0, 0, 128))
        img.save(img_path, format="PNG")
        
        metadata = MetadataParser.extract_image_metadata(str(img_path))
        
        assert metadata is not None
        assert metadata["width"] == 150
        assert metadata["height"] == 150
        assert metadata["format"] == "PNG"
        assert metadata["mode"] == "RGBA"

    def test_extract_grayscale_image_metadata(self, tmp_path):
        """Test extracting metadata from a grayscale image."""
        from PIL import Image
        
        # Create a simple test grayscale image
        img_path = tmp_path / "test_gray.png"
        img = Image.new("L", (300, 400), color=128)
        img.save(img_path, format="PNG")
        
        metadata = MetadataParser.extract_image_metadata(str(img_path))
        
        assert metadata is not None
        assert metadata["width"] == 300
        assert metadata["height"] == 400
        assert metadata["format"] == "PNG"
        assert metadata["mode"] == "L"

    def test_extract_non_image_returns_none(self, tmp_path):
        """Test that non-image files return None."""
        text_file = tmp_path / "test.txt"
        text_file.write_text("This is not an image")
        
        metadata = MetadataParser.extract_image_metadata(str(text_file))
        
        assert metadata is None

    def test_extract_nonexistent_file_returns_none(self, tmp_path):
        """Test that non-existent files return None."""
        img_path = tmp_path / "nonexistent.png"
        
        metadata = MetadataParser.extract_image_metadata(str(img_path))
        
        assert metadata is None

    def test_extract_all_metadata_includes_image_metadata(self, tmp_path):
        """Test that extract_all_metadata includes image metadata for images."""
        from PIL import Image
        
        # Create a test image
        img_path = tmp_path / "photo.jpg"
        img = Image.new("RGB", (800, 600), color="green")
        img.save(img_path, format="JPEG")
        
        metadata = MetadataParser.extract_all_metadata(str(img_path))
        
        assert "width" in metadata
        assert "height" in metadata
        assert "format" in metadata
        assert "mode" in metadata
        assert metadata["width"] == 800
        assert metadata["height"] == 600

    def test_extract_all_metadata_with_image_and_sidecar(self, tmp_path):
        """Test that image metadata and sidecar metadata are both included."""
        from PIL import Image
        
        # Create a test image
        img_path = tmp_path / "photo.png"
        img = Image.new("RGB", (1920, 1080), color="yellow")
        img.save(img_path, format="PNG")
        
        # Create a sidecar file
        sidecar_path = tmp_path / "photo.png.json"
        sidecar_path.write_text('{"title": "My Photo", "description": "A test photo"}')
        
        metadata = MetadataParser.extract_all_metadata(str(img_path))
        
        # Should have both image metadata and sidecar metadata
        assert metadata["width"] == 1920
        assert metadata["height"] == 1080
        assert metadata["format"] == "PNG"
        assert metadata["title"] == "My Photo"
        assert metadata["description"] == "A test photo"
