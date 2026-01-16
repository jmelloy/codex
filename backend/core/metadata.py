"""Metadata parsers for various formats."""

import json
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional
from pathlib import Path
import frontmatter


class MetadataParser:
    """Base class for metadata parsers."""

    @staticmethod
    def parse_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
        """Parse markdown frontmatter."""
        try:
            post = frontmatter.loads(content)
            return dict(post.metadata), post.content
        except Exception as e:
            print(f"Error parsing frontmatter: {e}")
            return {}, content

    @staticmethod
    def parse_json_sidecar(filepath: str) -> Optional[Dict[str, Any]]:
        """Parse JSON sidecar file."""
        sidecar_path = f"{filepath}.json"
        if not Path(sidecar_path).exists():
            # Try with dot prefix
            sidecar_path = str(Path(filepath).parent / f".{Path(filepath).name}.json")
            if not Path(sidecar_path).exists():
                return None

        try:
            with open(sidecar_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error parsing JSON sidecar: {e}")
            return None

    @staticmethod
    def parse_xml_sidecar(filepath: str) -> Optional[Dict[str, Any]]:
        """Parse XML sidecar file."""
        sidecar_path = f"{filepath}.xml"
        if not Path(sidecar_path).exists():
            # Try with dot prefix
            sidecar_path = str(Path(filepath).parent / f".{Path(filepath).name}.xml")
            if not Path(sidecar_path).exists():
                return None

        try:
            tree = ET.parse(sidecar_path)
            root = tree.getroot()
            return MetadataParser._xml_to_dict(root)
        except Exception as e:
            print(f"Error parsing XML sidecar: {e}")
            return None

    @staticmethod
    def _xml_to_dict(element: ET.Element) -> Dict[str, Any]:
        """Convert XML element to dictionary."""
        result: Dict[str, Any] = {}

        # Add attributes
        if element.attrib:
            result.update(element.attrib)

        # Add children
        for child in element:
            child_data = MetadataParser._xml_to_dict(child)
            if child.tag in result:
                # Handle multiple children with same tag
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data

        # Add text content
        if element.text and element.text.strip():
            if result:
                result["_text"] = element.text.strip()
            else:
                return element.text.strip()

        return result if result else {}

    @staticmethod
    def parse_markdown_sidecar(filepath: str) -> Optional[Dict[str, Any]]:
        """Parse markdown sidecar file."""
        sidecar_path = f"{filepath}.md"
        if not Path(sidecar_path).exists():
            # Try with dot prefix
            sidecar_path = str(Path(filepath).parent / f".{Path(filepath).name}.md")
            if not Path(sidecar_path).exists():
                return None

        try:
            with open(sidecar_path, "r") as f:
                content = f.read()
            metadata, _ = MetadataParser.parse_frontmatter(content)
            return metadata
        except Exception as e:
            print(f"Error parsing markdown sidecar: {e}")
            return None

    @staticmethod
    def extract_all_metadata(filepath: str, content: Optional[str] = None) -> Dict[str, Any]:
        """Extract all available metadata from a file."""
        metadata: Dict[str, Any] = {}

        # Try frontmatter if content provided and file is markdown
        if content and filepath.endswith(".md"):
            fm_metadata, _ = MetadataParser.parse_frontmatter(content)
            metadata.update(fm_metadata)

        # Try sidecar files
        json_metadata = MetadataParser.parse_json_sidecar(filepath)
        if json_metadata:
            metadata.update(json_metadata)

        xml_metadata = MetadataParser.parse_xml_sidecar(filepath)
        if xml_metadata:
            metadata.update(xml_metadata)

        markdown_metadata = MetadataParser.parse_markdown_sidecar(filepath)
        if markdown_metadata:
            metadata.update(markdown_metadata)

        return metadata

    @staticmethod
    def write_json_sidecar(filepath: str, metadata: Dict[str, Any], use_dot_prefix: bool = True):
        """Write metadata to JSON sidecar file."""
        if use_dot_prefix:
            sidecar_path = str(Path(filepath).parent / f".{Path(filepath).name}.json")
        else:
            sidecar_path = f"{filepath}.json"

        try:
            with open(sidecar_path, "w") as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            print(f"Error writing JSON sidecar: {e}")

    @staticmethod
    def write_markdown_sidecar(filepath: str, metadata: Dict[str, Any], content: str = "", use_dot_prefix: bool = True):
        """Write metadata to markdown sidecar file with frontmatter."""
        if use_dot_prefix:
            sidecar_path = str(Path(filepath).parent / f".{Path(filepath).name}.md")
        else:
            sidecar_path = f"{filepath}.md"

        try:
            post = frontmatter.Post(content, **metadata)
            with open(sidecar_path, "w") as f:
                f.write(frontmatter.dumps(post))
        except Exception as e:
            print(f"Error writing markdown sidecar: {e}")
