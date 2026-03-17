"""S3-based plugin client for downloading and caching plugins.

Replaces the HTTP-based PluginServiceClient. Downloads plugin zip archives
from S3, caches them locally, and extracts to the plugins directory.
"""

import io
import logging
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3PluginClient:
    """Client for downloading plugins from S3.

    Downloads plugin zip archives from an S3 bucket, caches them locally to
    avoid redundant downloads, and extracts them to the plugins directory.

    Plugins are stored in S3 as zip files at:
        {plugin_id}/{version}/plugin.zip

    Each zip contains the full plugin directory structure including
    manifest.yml at the root.
    """

    def __init__(
        self,
        bucket_name: str,
        plugins_dir: Path,
        cache_dir: Path | None = None,
        region_name: str | None = None,
    ):
        self.bucket_name = bucket_name
        self.plugins_dir = Path(plugins_dir)
        self.cache_dir = Path(cache_dir or plugins_dir / ".cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        session_kwargs: dict[str, Any] = {}
        if region_name:
            session_kwargs["region_name"] = region_name

        self._s3 = boto3.client("s3", **session_kwargs)

    def list_plugin_versions(self, plugin_id: str) -> list[str]:
        """List all versions available for a plugin in S3.

        Args:
            plugin_id: Plugin identifier

        Returns:
            List of version strings, sorted newest first
        """
        prefix = f"{plugin_id}/"
        versions = set()

        paginator = self._s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix, Delimiter="/"):
            for common_prefix in page.get("CommonPrefixes", []):
                # Key format: {plugin_id}/{version}/
                version = common_prefix["Prefix"].rstrip("/").split("/")[-1]
                versions.add(version)

        return sorted(versions, reverse=True)

    def download_plugin(self, plugin_id: str, version: str) -> Path:
        """Download and extract a plugin zip archive from S3.

        Downloads {plugin_id}/{version}/plugin.zip and extracts it to the
        local plugins directory. Uses local caching to avoid re-downloading
        unchanged archives.

        Args:
            plugin_id: Plugin identifier
            version: Plugin version string

        Returns:
            Path to the extracted plugin directory
        """
        s3_key = f"{plugin_id}/{version}/plugin.zip"
        plugin_dir = self.plugins_dir / plugin_id
        cache_marker = self.cache_dir / f"{plugin_id}-{version}.cached"

        # Check if already cached and extracted
        if cache_marker.exists() and plugin_dir.exists():
            logger.debug(f"Plugin {plugin_id} v{version} already cached")
            return plugin_dir

        logger.info(f"Downloading plugin {plugin_id} v{version} from s3://{self.bucket_name}/{s3_key}")

        # Download zip to a temp file, extract to a staging directory on the same
        # filesystem, then atomically replace the plugin directory so that stale
        # files from previous versions are never left on disk.
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp_path = tmp.name

        # Use a unique staging directory inside plugins_dir so that rename() stays
        # on one filesystem and concurrent downloads for the same plugin_id do not
        # collide on the staging path.
        staging_dir = Path(tempfile.mkdtemp(dir=self.plugins_dir, prefix=f".tmp-{plugin_id}-"))

        try:
            self._s3.download_file(self.bucket_name, s3_key, tmp_path)

            # Extract to staging directory
            try:
                with zipfile.ZipFile(tmp_path, "r") as zf:
                    zf.extractall(staging_dir)
            except Exception:
                try:
                    shutil.rmtree(staging_dir)
                except OSError:
                    logger.warning(f"Failed to remove staging dir {staging_dir} after extraction error")
                raise

            # Atomically replace old plugin directory with the freshly extracted one
            if plugin_dir.exists():
                shutil.rmtree(plugin_dir)
            staging_dir.rename(plugin_dir)
        finally:
            os.unlink(tmp_path)

        # Mark as cached
        cache_marker.write_text(version)
        logger.info(f"Plugin {plugin_id} v{version} extracted to {plugin_dir}")

        return plugin_dir

    def download_file(self, s3_key: str, local_path: Path) -> Path:
        """Download a single file from S3.

        Args:
            s3_key: S3 object key
            local_path: Local path to save the file

        Returns:
            Path to the downloaded file
        """
        local_path.parent.mkdir(parents=True, exist_ok=True)
        self._s3.download_file(self.bucket_name, s3_key, str(local_path))
        return local_path

    def get_manifest(self, plugin_id: str, version: str) -> dict[str, Any] | None:
        """Download and parse a plugin's manifest from S3.

        Reads the manifest from within the plugin zip archive without
        extracting the full archive.

        Args:
            plugin_id: Plugin identifier
            version: Plugin version string

        Returns:
            Parsed manifest dict, or None if not found
        """
        import yaml

        key = f"{plugin_id}/{version}/plugin.zip"
        try:
            response = self._s3.get_object(Bucket=self.bucket_name, Key=key)
            zip_bytes = response["Body"].read()

            with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
                if "manifest.yml" in zf.namelist():
                    manifest_data = zf.read("manifest.yml").decode("utf-8")
                    return yaml.safe_load(manifest_data)
            return None
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise

    def sync_plugin(self, plugin_id: str, version: str) -> Path:
        """Sync a specific plugin version, downloading only if needed.

        Args:
            plugin_id: Plugin identifier
            version: Version to sync

        Returns:
            Path to the plugin directory
        """
        cache_marker = self.cache_dir / f"{plugin_id}-{version}.cached"
        plugin_dir = self.plugins_dir / plugin_id

        if cache_marker.exists() and plugin_dir.exists():
            return plugin_dir

        return self.download_plugin(plugin_id, version)

    def invalidate_cache(self, plugin_id: str | None = None) -> None:
        """Invalidate cached plugin downloads.

        Args:
            plugin_id: If specified, only invalidate this plugin's cache.
                       If None, invalidate all cached plugins.
        """
        if plugin_id:
            for marker in self.cache_dir.glob(f"{plugin_id}-*.cached"):
                marker.unlink()
        else:
            for marker in self.cache_dir.glob("*.cached"):
                marker.unlink()
