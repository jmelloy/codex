"""DynamoDB-based plugin registry.

Scans the DynamoDB plugin registry table (populated by S3 event
notifications) to build the list of available plugins and their versions.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


@dataclass
class PluginVersionInfo:
    """Metadata for a specific plugin version from DynamoDB."""

    plugin_id: str
    version: str
    name: str
    plugin_type: str
    description: str = ""
    author: str = ""
    s3_bucket: str = ""
    s3_prefix: str = ""
    manifest: dict[str, Any] = field(default_factory=dict)
    indexed_at: str = ""


class DynamoPluginRegistry:
    """Reads plugin metadata from DynamoDB.

    The DynamoDB table is populated automatically by S3 event
    notifications when plugin archives are uploaded. This class
    provides a read-only view of the registry.
    """

    def __init__(self, table_name: str, region_name: str | None = None):
        session_kwargs: dict[str, Any] = {}
        if region_name:
            session_kwargs["region_name"] = region_name

        dynamodb = boto3.resource("dynamodb", **session_kwargs)
        self._table = dynamodb.Table(table_name)
        self._table_name = table_name

    def list_plugins(self) -> list[PluginVersionInfo]:
        """List all plugins (latest version of each).

        Scans the table and returns the highest version for each plugin_id.

        Returns:
            List of PluginVersionInfo for each plugin's latest version
        """
        latest: dict[str, PluginVersionInfo] = {}

        try:
            response = self._table.scan()
            items = response.get("Items", [])

            # Handle pagination
            while "LastEvaluatedKey" in response:
                response = self._table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
                items.extend(response.get("Items", []))
        except ClientError as e:
            logger.error(f"Error scanning DynamoDB table {self._table_name}: {e}")
            return []

        for item in items:
            info = self._item_to_info(item)
            existing = latest.get(info.plugin_id)
            if not existing or self._version_gt(info.version, existing.version):
                latest[info.plugin_id] = info

        return list(latest.values())

    def get_plugin(self, plugin_id: str) -> PluginVersionInfo | None:
        """Get the latest version info for a specific plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            PluginVersionInfo or None if not found
        """
        try:
            response = self._table.query(
                KeyConditionExpression=Key("plugin_id").eq(plugin_id),
                ScanIndexForward=False,  # Sort descending by version
                Limit=1,
            )
            items = response.get("Items", [])
            if items:
                return self._item_to_info(items[0])
        except ClientError as e:
            logger.error(f"Error querying plugin {plugin_id}: {e}")

        return None

    def get_plugin_version(self, plugin_id: str, version: str) -> PluginVersionInfo | None:
        """Get info for a specific plugin version.

        Args:
            plugin_id: Plugin identifier
            version: Version string

        Returns:
            PluginVersionInfo or None if not found
        """
        try:
            response = self._table.get_item(Key={"plugin_id": plugin_id, "version": version})
            item = response.get("Item")
            if item:
                return self._item_to_info(item)
        except ClientError as e:
            logger.error(f"Error getting plugin {plugin_id} v{version}: {e}")

        return None

    def get_all_versions(self, plugin_id: str) -> list[PluginVersionInfo]:
        """Get all versions for a specific plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            List of PluginVersionInfo, sorted newest first
        """
        try:
            response = self._table.query(
                KeyConditionExpression=Key("plugin_id").eq(plugin_id),
                ScanIndexForward=False,
            )
            items = response.get("Items", [])

            # Handle pagination
            while "LastEvaluatedKey" in response:
                response = self._table.query(
                    KeyConditionExpression=Key("plugin_id").eq(plugin_id),
                    ScanIndexForward=False,
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                )
                items.extend(response.get("Items", []))

            return [self._item_to_info(item) for item in items]
        except ClientError as e:
            logger.error(f"Error listing versions for {plugin_id}: {e}")
            return []

    def _item_to_info(self, item: dict[str, Any]) -> PluginVersionInfo:
        """Convert a DynamoDB item to a PluginVersionInfo."""
        manifest_raw = item.get("manifest", "{}")
        if isinstance(manifest_raw, str):
            try:
                manifest = json.loads(manifest_raw)
            except (json.JSONDecodeError, TypeError):
                manifest = {}
        else:
            manifest = manifest_raw

        return PluginVersionInfo(
            plugin_id=item["plugin_id"],
            version=item["version"],
            name=item.get("name", item["plugin_id"]),
            plugin_type=item.get("type", "unknown"),
            description=item.get("description", ""),
            author=item.get("author", ""),
            s3_bucket=item.get("s3_bucket", ""),
            s3_prefix=item.get("s3_prefix", ""),
            manifest=manifest,
            indexed_at=item.get("indexed_at", ""),
        )

    @staticmethod
    def _version_gt(a: str, b: str) -> bool:
        """Compare two version strings.

        Uses the YYYY.MM.release.sha format, falling back
        to lexicographic comparison.
        """
        try:
            a_parts = [int(x) for x in a.split(".")[:3]]
            b_parts = [int(x) for x in b.split(".")[:3]]
            return a_parts > b_parts
        except (ValueError, IndexError):
            return a > b
