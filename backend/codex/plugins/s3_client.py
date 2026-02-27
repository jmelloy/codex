"""S3-based plugin client for downloading and caching plugins.

Replaces the HTTP-based PluginServiceClient. Downloads plugin archives
from S3, caches them locally, and extracts to the plugins directory.
"""

import hashlib
import io
import logging
import os
import tarfile
import tempfile
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3PluginClient:
    """Client for downloading plugins from S3.

    Downloads plugin files from an S3 bucket, caches them locally to
    avoid redundant downloads, and extracts them to the plugins directory.
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
        """Download and extract a specific plugin version from S3.

        Downloads all files under {plugin_id}/{version}/ and extracts
        them to the local plugins directory. Uses local caching to
        avoid re-downloading unchanged files.

        Args:
            plugin_id: Plugin identifier
            version: Plugin version string

        Returns:
            Path to the extracted plugin directory
        """
        s3_prefix = f"{plugin_id}/{version}/"
        plugin_dir = self.plugins_dir / plugin_id
        cache_marker = self.cache_dir / f"{plugin_id}-{version}.cached"

        # Check if already cached and extracted
        if cache_marker.exists() and plugin_dir.exists():
            logger.debug(f"Plugin {plugin_id} v{version} already cached")
            return plugin_dir

        logger.info(f"Downloading plugin {plugin_id} v{version} from s3://{self.bucket_name}/{s3_prefix}")

        plugin_dir.mkdir(parents=True, exist_ok=True)

        # Download all files under the version prefix
        paginator = self._s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=s3_prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                # Relative path within the plugin: strip {plugin_id}/{version}/
                relative_path = key[len(s3_prefix) :]
                if not relative_path:
                    continue

                local_path = plugin_dir / relative_path
                local_path.parent.mkdir(parents=True, exist_ok=True)

                self._s3.download_file(self.bucket_name, key, str(local_path))
                logger.debug(f"  Downloaded: {relative_path}")

        # Mark as cached
        cache_marker.write_text(version)
        logger.info(f"Plugin {plugin_id} v{version} downloaded to {plugin_dir}")

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

        Args:
            plugin_id: Plugin identifier
            version: Plugin version string

        Returns:
            Parsed manifest dict, or None if not found
        """
        import yaml

        key = f"{plugin_id}/{version}/manifest.yml"
        try:
            response = self._s3.get_object(Bucket=self.bucket_name, Key=key)
            content = response["Body"].read().decode("utf-8")
            return yaml.safe_load(content)
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
