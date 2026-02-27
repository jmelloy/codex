"""Plugin catalog builder.

Scans a plugins directory, validates manifests, computes SHA-256 checksums
for each plugin archive, and maintains an in-memory catalog for serving.
"""

import hashlib
import io
import logging
import re
import tarfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class CatalogEntry:
    """A single plugin in the catalog."""

    plugin_id: str
    name: str
    version: str
    plugin_type: str
    description: str
    author: str
    manifest: dict[str, Any]
    archive_sha256: str
    archive_size: int
    plugin_dir: Path

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.plugin_id,
            "name": self.name,
            "version": self.version,
            "type": self.plugin_type,
            "description": self.description,
            "author": self.author,
            "sha256": self.archive_sha256,
            "archive_size": self.archive_size,
            "manifest": self.manifest,
        }


@dataclass
class PluginCatalog:
    """In-memory catalog of available plugins."""

    plugins_dir: Path
    entries: dict[str, CatalogEntry] = field(default_factory=dict)
    _archive_cache: dict[str, bytes] = field(default_factory=dict)

    def build(self) -> None:
        """Scan the plugins directory and build the catalog."""
        self.entries.clear()
        self._archive_cache.clear()

        if not self.plugins_dir.exists():
            logger.warning(f"Plugins directory does not exist: {self.plugins_dir}")
            return

        for item in sorted(self.plugins_dir.iterdir()):
            if not item.is_dir():
                continue
            # Skip non-plugin directories
            if item.name.startswith(".") or item.name in ("shared", "node_modules"):
                continue

            try:
                entry = self._load_plugin(item)
                if entry:
                    self.entries[entry.plugin_id] = entry
                    logger.info(f"Cataloged plugin: {entry.plugin_id} v{entry.version}")
            except Exception as e:
                logger.warning(f"Skipping {item.name}: {e}")

        logger.info(f"Catalog built with {len(self.entries)} plugins")

    def _load_plugin(self, plugin_dir: Path) -> CatalogEntry | None:
        """Load and validate a single plugin, compute its archive checksum."""
        manifest_data = self._read_manifest(plugin_dir)
        if not manifest_data:
            return None

        self._validate_manifest(manifest_data)

        archive_bytes = self._build_archive(plugin_dir)
        sha256 = hashlib.sha256(archive_bytes).hexdigest()
        self._archive_cache[manifest_data["id"]] = archive_bytes

        return CatalogEntry(
            plugin_id=manifest_data["id"],
            name=manifest_data["name"],
            version=manifest_data["version"],
            plugin_type=manifest_data["type"],
            description=manifest_data.get("description", ""),
            author=manifest_data.get("author", ""),
            manifest=manifest_data,
            archive_sha256=sha256,
            archive_size=len(archive_bytes),
            plugin_dir=plugin_dir,
        )

    def _read_manifest(self, plugin_dir: Path) -> dict[str, Any] | None:
        """Read manifest from a plugin directory."""
        manifest_files = [
            "manifest.yml",
            "manifest.yaml",
            "plugin.yaml",
            "theme.yaml",
            "integration.yaml",
        ]
        for name in manifest_files:
            path = plugin_dir / name
            if path.exists():
                with open(path) as f:
                    return yaml.safe_load(f)
        return None

    def _validate_manifest(self, manifest: dict[str, Any]) -> None:
        """Validate required manifest fields."""
        for field_name in ("id", "name", "version", "type"):
            if field_name not in manifest:
                raise ValueError(f"Missing required field: {field_name}")

        if not re.match(r"^[a-z0-9-]+$", manifest["id"]):
            raise ValueError(f"Invalid plugin ID: {manifest['id']}")

        if not re.match(r"^\d+\.\d+\.\d+$", manifest["version"]):
            raise ValueError(f"Invalid version: {manifest['version']}")

        valid_types = {"view", "theme", "integration"}
        if manifest["type"] not in valid_types:
            raise ValueError(f"Invalid type: {manifest['type']}")

    def _build_archive(self, plugin_dir: Path) -> bytes:
        """Build a tar.gz archive of a plugin directory."""
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            tar.add(str(plugin_dir), arcname=plugin_dir.name)
        return buf.getvalue()

    def get_entry(self, plugin_id: str) -> CatalogEntry | None:
        return self.entries.get(plugin_id)

    def get_archive(self, plugin_id: str) -> bytes | None:
        """Get the cached archive bytes for a plugin."""
        return self._archive_cache.get(plugin_id)

    def list_entries(self, plugin_type: str | None = None) -> list[CatalogEntry]:
        entries = list(self.entries.values())
        if plugin_type:
            entries = [e for e in entries if e.plugin_type == plugin_type]
        return entries
