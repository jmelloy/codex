"""Metadata parsers for various formats."""

import json
import logging
import xml.etree.ElementTree as ET
from datetime import date, datetime
from pathlib import Path
from typing import Any

import frontmatter
from PIL import Image

logger = logging.getLogger(__name__)


def sanitize_metadata(data: Any) -> Any:
    """Recursively convert datetime objects to ISO format strings for JSON serialization."""
    if isinstance(data, datetime):
        return data.isoformat()
    elif isinstance(data, date):
        return data.isoformat()
    elif isinstance(data, dict):
        return {k: sanitize_metadata(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_metadata(item) for item in data]
    return data


class MetadataParser:
    """Base class for metadata parsers."""

    @staticmethod
    def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
        """Parse markdown frontmatter."""
        try:
            post = frontmatter.loads(content)
            # Sanitize metadata to convert datetime objects to strings for JSON serialization
            metadata = sanitize_metadata(dict(post.metadata))
            return metadata, post.content
        except Exception as e:
            logger.error(f"Error parsing frontmatter: {e}")
            return {}, content

    @staticmethod
    def write_frontmatter(content: str, properties: dict[str, Any]) -> str:
        """Combine content with frontmatter properties.

        Args:
            content: The main content (without frontmatter)
            properties: Dictionary of properties to write as frontmatter

        Returns:
            The content with frontmatter prepended
        """
        try:
            post = frontmatter.Post(content, **properties)
            return frontmatter.dumps(post)
        except Exception as e:
            logger.error(f"Error writing frontmatter: {e}")
            return content

    @staticmethod
    def parse_json_sidecar(filepath: str) -> dict[str, Any] | None:
        """Parse JSON sidecar file."""
        sidecar_path = f"{filepath}.json"
        if not Path(sidecar_path).exists():
            # Try with dot prefix
            sidecar_path = str(Path(filepath).parent / f".{Path(filepath).name}.json")
            if not Path(sidecar_path).exists():
                return None

        try:
            with open(sidecar_path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error parsing JSON sidecar: {e}", exc_info=True)
            return None

    @staticmethod
    def parse_xml_sidecar(filepath: str) -> dict[str, Any] | None:
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
            logger.error(f"Error parsing XML sidecar: {e}", exc_info=True)
            return None

    @staticmethod
    def _xml_to_dict(element: ET.Element) -> dict[str, Any]:
        """Convert XML element to dictionary."""
        result: dict[str, Any] = {}

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
    def parse_markdown_sidecar(filepath: str) -> dict[str, Any] | None:
        """Parse markdown sidecar file."""
        sidecar_path = f"{filepath}.md"
        if not Path(sidecar_path).exists():
            # Try with dot prefix
            sidecar_path = str(Path(filepath).parent / f".{Path(filepath).name}.md")
            if not Path(sidecar_path).exists():
                return None

        try:
            with open(sidecar_path) as f:
                content = f.read()
            metadata, _ = MetadataParser.parse_frontmatter(content)
            return metadata
        except Exception as e:
            logger.error(f"Error parsing markdown sidecar: {e}", exc_info=True)
            return None

    @staticmethod
    def extract_image_metadata(filepath: str) -> dict[str, Any] | None:
        """Extract metadata from an image file.
        
        Returns a dictionary with:
        - width: Image width in pixels
        - height: Image height in pixels
        - format: Image format (e.g., PNG, JPEG, GIF)
        - mode: Image mode (e.g., RGB, RGBA, L for grayscale)
        
        Returns None if the file is not an image or cannot be read.
        """
        # Check if file might be an image based on extension (performance optimization)
        # Common image extensions supported by Pillow
        image_extensions = {
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif', 
            '.webp', '.ico', '.svg', '.heic', '.heif', '.avif'
        }
        file_ext = Path(filepath).suffix.lower()
        if file_ext not in image_extensions:
            return None
            
        try:
            with Image.open(filepath) as img:
                return {
                    "width": img.width,
                    "height": img.height,
                    "format": img.format,
                    "mode": img.mode,
                }
        except Exception as e:
            logger.debug(f"Could not extract image metadata from {filepath}: {e}")
            return None

    @staticmethod
    def extract_all_metadata(filepath: str, content: str | None = None) -> dict[str, Any]:
        """Extract all available metadata from a file.
        
        Priority order (later sources override earlier ones):
        1. Image metadata (automatic extraction)
        2. Frontmatter (for markdown files)
        3. Sidecar files (JSON, XML, Markdown)
        
        This allows user-provided metadata in sidecars to override automatic extraction.
        """
        metadata: dict[str, Any] = {}

        # Try extracting image metadata first (so sidecars can override)
        image_metadata = MetadataParser.extract_image_metadata(filepath)
        if image_metadata:
            metadata.update(image_metadata)

        # Try frontmatter for markdown files - read from disk if content not provided
        if filepath.endswith(".md"):
            if content is None:
                try:
                    with open(filepath, "r") as f:
                        content = f.read()
                except Exception as e:
                    logger.debug(f"Could not read markdown file {filepath}: {e}")
            if content:
                fm_metadata, _ = MetadataParser.parse_frontmatter(content)
                metadata.update(fm_metadata)

        # Try sidecar files (these have highest priority and can override everything)
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
    def write_json_sidecar(filepath: str, metadata: dict[str, Any], use_dot_prefix: bool = True):
        """Write metadata to JSON sidecar file."""
        if use_dot_prefix:
            sidecar_path = str(Path(filepath).parent / f".{Path(filepath).name}.json")
        else:
            sidecar_path = f"{filepath}.json"

        logger.debug(f"Writing JSON sidecar to {sidecar_path} with metadata: {metadata}")
        try:
            with open(sidecar_path, "w") as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Error writing JSON sidecar: {e}", exc_info=True)

    @staticmethod
    def write_markdown_sidecar(filepath: str, metadata: dict[str, Any], content: str = "", use_dot_prefix: bool = True):
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
            logger.error(f"Error writing markdown sidecar: {e}", exc_info=True)

    @staticmethod
    def resolve_sidecar(filepath: str) -> tuple[str, str | None]:
        """Check for existence of sidecar files and return the path if found."""

        suffixes = [".json", ".xml", ".md"]

        for suffix in suffixes:
            # file = regular, sidecar = no dot prefix
            sidecar = Path(f"{filepath}{suffix}")
            if sidecar.exists():
                return (filepath, str(sidecar))
            
            # file = regular, sidecar = dot prefix
            sidecar_dot = Path(filepath).parent / f".{Path(filepath).name}{suffix}"
            if sidecar_dot.exists():
                return (filepath, str(sidecar_dot))
            
            # file = sidecar
            if filepath.endswith(suffix):
                regular_file = filepath.removesuffix(suffix)
                if Path(regular_file).exists():
                    return (regular_file, filepath)

            # file = dot-prefixed sidecar
            if Path(filepath).name.startswith(".") and filepath.endswith(suffix):
                file = Path(filepath).parent / Path(filepath).name.removesuffix(suffix).removeprefix(".")
                if Path(file).exists():
                    return (str(file), filepath)

        return (filepath, None)

    @staticmethod
    def write_sidecar(filepath: str, metadata: dict[str, Any]):
        """Write metadata to appropriate sidecar file based on existing files or default to JSON."""
        _, sidecar = MetadataParser.resolve_sidecar(filepath)
        logger.debug(f"Resolved sidecar for {filepath}: {sidecar}")
        if sidecar:
            if sidecar.endswith(".json"):
                MetadataParser.write_json_sidecar(filepath, metadata, use_dot_prefix=Path(sidecar).name.startswith("."))
            elif sidecar.endswith(".md"):
                MetadataParser.write_markdown_sidecar(
                    filepath, metadata, use_dot_prefix=Path(sidecar).name.startswith(".")
                )
            else:
                # Default to JSON if XML or unknown
                MetadataParser.write_json_sidecar(filepath, metadata, use_dot_prefix=Path(sidecar).name.startswith("."))
        else:
            # No existing sidecar - default to JSON with dot prefix
            MetadataParser.write_json_sidecar(filepath, metadata, use_dot_prefix=True)
