"""Plugin service client for downloading and verifying plugins.

Connects to the Codex Plugin Service to:
1. Fetch the plugin catalog (manifests + SHA-256 checksums)
2. Download plugin archives
3. Verify archive integrity against expected checksums
4. Extract verified plugins to the local plugins directory
"""

import hashlib
import io
import logging
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class PluginVerificationError(Exception):
    """Raised when a plugin archive fails integrity verification."""


@dataclass
class RemotePlugin:
    """A plugin available from the plugin service."""

    plugin_id: str
    name: str
    version: str
    plugin_type: str
    description: str
    author: str
    sha256: str
    archive_size: int
    manifest: dict[str, Any]


class PluginServiceClient:
    """Client for the Codex Plugin Service.

    Handles discovery, download, verification, and installation of plugins
    from a remote plugin service.
    """

    def __init__(self, service_url: str, plugins_dir: Path, timeout: int = 30):
        """Initialize the client.

        Args:
            service_url: Base URL of the plugin service (e.g. http://plugin-service:8090)
            plugins_dir: Local directory where plugins are installed
            timeout: HTTP request timeout in seconds
        """
        self.service_url = service_url.rstrip("/")
        self.plugins_dir = Path(plugins_dir)
        self.timeout = timeout

    async def fetch_catalog(self, plugin_type: str | None = None) -> list[RemotePlugin]:
        """Fetch the plugin catalog from the service.

        Args:
            plugin_type: Optional filter by type (view, theme, integration)

        Returns:
            List of available remote plugins
        """
        params = {}
        if plugin_type:
            params["plugin_type"] = plugin_type

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.service_url}/api/v1/catalog", params=params)
            response.raise_for_status()

        data = response.json()
        return [
            RemotePlugin(
                plugin_id=p["id"],
                name=p["name"],
                version=p["version"],
                plugin_type=p["type"],
                description=p.get("description", ""),
                author=p.get("author", ""),
                sha256=p["sha256"],
                archive_size=p["archive_size"],
                manifest=p.get("manifest", {}),
            )
            for p in data.get("plugins", [])
        ]

    async def get_plugin_info(self, plugin_id: str) -> RemotePlugin:
        """Fetch info for a specific plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Remote plugin info

        Raises:
            httpx.HTTPStatusError: If plugin not found (404)
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.service_url}/api/v1/catalog/{plugin_id}")
            response.raise_for_status()

        p = response.json()
        return RemotePlugin(
            plugin_id=p["id"],
            name=p["name"],
            version=p["version"],
            plugin_type=p["type"],
            description=p.get("description", ""),
            author=p.get("author", ""),
            sha256=p["sha256"],
            archive_size=p["archive_size"],
            manifest=p.get("manifest", {}),
        )

    async def download_and_verify(self, plugin_id: str, expected_sha256: str | None = None) -> bytes:
        """Download a plugin archive and verify its SHA-256 checksum.

        Args:
            plugin_id: Plugin identifier
            expected_sha256: Expected SHA-256 hash. If None, fetches it from the catalog.

        Returns:
            Verified archive bytes

        Raises:
            PluginVerificationError: If checksum does not match
        """
        if not expected_sha256:
            info = await self.get_plugin_info(plugin_id)
            expected_sha256 = info.sha256

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.service_url}/api/v1/catalog/{plugin_id}/download")
            response.raise_for_status()

        archive_bytes = response.content

        # Verify checksum from header if present
        header_sha256 = response.headers.get("x-checksum-sha256")
        if header_sha256 and header_sha256 != expected_sha256:
            raise PluginVerificationError(
                f"Plugin {plugin_id}: catalog checksum ({expected_sha256}) "
                f"does not match header checksum ({header_sha256})"
            )

        # Verify the actual content checksum
        actual_sha256 = hashlib.sha256(archive_bytes).hexdigest()
        if actual_sha256 != expected_sha256:
            raise PluginVerificationError(
                f"Plugin {plugin_id}: expected SHA-256 {expected_sha256}, "
                f"got {actual_sha256}. Archive may be corrupted or tampered with."
            )

        logger.info(f"Plugin {plugin_id}: SHA-256 verified ({actual_sha256})")
        return archive_bytes

    async def install_plugin(self, plugin_id: str, expected_sha256: str | None = None) -> Path:
        """Download, verify, and extract a plugin to the plugins directory.

        Args:
            plugin_id: Plugin identifier
            expected_sha256: Expected SHA-256 hash (fetched from catalog if omitted)

        Returns:
            Path to the installed plugin directory

        Raises:
            PluginVerificationError: If verification fails
        """
        archive_bytes = await self.download_and_verify(plugin_id, expected_sha256)

        # Extract to plugins directory
        plugin_path = self.plugins_dir / plugin_id
        buf = io.BytesIO(archive_bytes)
        with tarfile.open(fileobj=buf, mode="r:gz") as tar:
            # Security: check for path traversal
            for member in tar.getmembers():
                member_path = Path(member.name)
                if member_path.is_absolute() or ".." in member_path.parts:
                    raise PluginVerificationError(
                        f"Plugin {plugin_id}: archive contains unsafe path: {member.name}"
                    )

            tar.extractall(path=str(self.plugins_dir))

        logger.info(f"Plugin {plugin_id}: installed to {plugin_path}")
        return plugin_path

    async def sync_plugins(self) -> dict[str, Any]:
        """Sync local plugins with the remote catalog.

        Downloads and installs plugins that are missing locally or have
        a newer version available. Verifies checksums for all downloads.

        Returns:
            Summary of sync results
        """
        catalog = await self.fetch_catalog()

        installed = []
        updated = []
        skipped = []
        failed = []

        for remote in catalog:
            local_dir = self.plugins_dir / remote.plugin_id
            try:
                if not local_dir.exists():
                    await self.install_plugin(remote.plugin_id, remote.sha256)
                    installed.append(remote.plugin_id)
                else:
                    # Check if local version matches
                    local_version = self._get_local_version(local_dir)
                    if local_version != remote.version:
                        await self.install_plugin(remote.plugin_id, remote.sha256)
                        updated.append(remote.plugin_id)
                    else:
                        skipped.append(remote.plugin_id)
            except Exception as e:
                logger.error(f"Failed to sync plugin {remote.plugin_id}: {e}")
                failed.append({"id": remote.plugin_id, "error": str(e)})

        return {
            "installed": installed,
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
        }

    def _get_local_version(self, plugin_dir: Path) -> str | None:
        """Read the version from a local plugin's manifest."""
        import yaml

        manifest_files = ["manifest.yml", "manifest.yaml", "plugin.yaml", "theme.yaml", "integration.yaml"]
        for name in manifest_files:
            path = plugin_dir / name
            if path.exists():
                with open(path) as f:
                    data = yaml.safe_load(f)
                    return data.get("version")
        return None

    @staticmethod
    def verify_archive(archive_bytes: bytes, expected_sha256: str) -> bool:
        """Verify an archive's SHA-256 checksum.

        Args:
            archive_bytes: The archive content
            expected_sha256: Expected hex-encoded SHA-256 hash

        Returns:
            True if checksum matches
        """
        actual = hashlib.sha256(archive_bytes).hexdigest()
        return actual == expected_sha256
