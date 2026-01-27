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
