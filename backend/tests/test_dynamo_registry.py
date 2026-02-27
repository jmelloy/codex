"""Tests for the DynamoDB plugin registry."""

import json
from unittest.mock import MagicMock, patch

import pytest

from codex.plugins.dynamo_registry import DynamoPluginRegistry, PluginVersionInfo


@pytest.fixture
def mock_table():
    with patch("boto3.resource") as mock_resource:
        table = MagicMock()
        mock_resource.return_value.Table.return_value = table
        yield table


@pytest.fixture
def registry(mock_table):
    return DynamoPluginRegistry(table_name="test-table", region_name="us-east-1")


def _make_item(plugin_id, version, name="Test", plugin_type="theme", **kwargs):
    """Create a DynamoDB item dict."""
    return {
        "plugin_id": plugin_id,
        "version": version,
        "name": name,
        "type": plugin_type,
        "description": kwargs.get("description", ""),
        "author": kwargs.get("author", ""),
        "s3_bucket": kwargs.get("s3_bucket", "test-bucket"),
        "s3_prefix": kwargs.get("s3_prefix", f"{plugin_id}/{version}/"),
        "manifest": json.dumps(kwargs.get("manifest", {"id": plugin_id, "version": version})),
        "indexed_at": kwargs.get("indexed_at", "2026-02-27T00:00:00Z"),
    }


def test_list_plugins_returns_latest(registry, mock_table):
    """Test that list_plugins returns the latest version of each plugin."""
    mock_table.scan.return_value = {
        "Items": [
            _make_item("plugin-a", "2026.01.1.abc"),
            _make_item("plugin-a", "2026.02.1.def"),
            _make_item("plugin-b", "2026.01.1.ghi"),
        ]
    }

    result = registry.list_plugins()
    assert len(result) == 2

    by_id = {p.plugin_id: p for p in result}
    assert by_id["plugin-a"].version == "2026.02.1.def"
    assert by_id["plugin-b"].version == "2026.01.1.ghi"


def test_list_plugins_handles_pagination(registry, mock_table):
    """Test that list_plugins handles DynamoDB pagination."""
    mock_table.scan.side_effect = [
        {"Items": [_make_item("plugin-a", "1.0.0")], "LastEvaluatedKey": {"pk": "x"}},
        {"Items": [_make_item("plugin-b", "2.0.0")]},
    ]

    result = registry.list_plugins()
    assert len(result) == 2


def test_list_plugins_empty(registry, mock_table):
    """Test list_plugins with empty table."""
    mock_table.scan.return_value = {"Items": []}
    result = registry.list_plugins()
    assert result == []


def test_get_plugin(registry, mock_table):
    """Test getting the latest version of a specific plugin."""
    mock_table.query.return_value = {
        "Items": [_make_item("test-plugin", "2026.02.3.abc", name="Test Plugin")]
    }

    result = registry.get_plugin("test-plugin")
    assert result is not None
    assert result.plugin_id == "test-plugin"
    assert result.version == "2026.02.3.abc"
    assert result.name == "Test Plugin"


def test_get_plugin_not_found(registry, mock_table):
    """Test getting a non-existent plugin returns None."""
    mock_table.query.return_value = {"Items": []}
    result = registry.get_plugin("nonexistent")
    assert result is None


def test_get_plugin_version(registry, mock_table):
    """Test getting a specific plugin version."""
    mock_table.get_item.return_value = {
        "Item": _make_item("test-plugin", "2026.02.1.abc")
    }

    result = registry.get_plugin_version("test-plugin", "2026.02.1.abc")
    assert result is not None
    assert result.version == "2026.02.1.abc"


def test_get_plugin_version_not_found(registry, mock_table):
    """Test getting a non-existent version returns None."""
    mock_table.get_item.return_value = {}
    result = registry.get_plugin_version("test-plugin", "999.99.99.xxx")
    assert result is None


def test_get_all_versions(registry, mock_table):
    """Test listing all versions of a plugin."""
    mock_table.query.return_value = {
        "Items": [
            _make_item("test-plugin", "2026.02.2.def"),
            _make_item("test-plugin", "2026.02.1.abc"),
            _make_item("test-plugin", "2026.01.1.ghi"),
        ]
    }

    result = registry.get_all_versions("test-plugin")
    assert len(result) == 3
    assert result[0].version == "2026.02.2.def"


def test_manifest_parsing_json_string(registry, mock_table):
    """Test that JSON string manifests are parsed correctly."""
    manifest = {"id": "test", "name": "Test", "version": "1.0.0", "type": "theme"}
    mock_table.query.return_value = {
        "Items": [
            {
                "plugin_id": "test",
                "version": "1.0.0",
                "name": "Test",
                "type": "theme",
                "manifest": json.dumps(manifest),
                "s3_prefix": "test/1.0.0/",
            }
        ]
    }

    result = registry.get_plugin("test")
    assert result is not None
    assert result.manifest["id"] == "test"


def test_manifest_parsing_dict(registry, mock_table):
    """Test that dict manifests (already parsed) work too."""
    manifest = {"id": "test", "name": "Test"}
    mock_table.query.return_value = {
        "Items": [
            {
                "plugin_id": "test",
                "version": "1.0.0",
                "name": "Test",
                "type": "theme",
                "manifest": manifest,
                "s3_prefix": "test/1.0.0/",
            }
        ]
    }

    result = registry.get_plugin("test")
    assert result is not None
    assert result.manifest["id"] == "test"


def test_version_comparison():
    """Test version comparison logic."""
    assert DynamoPluginRegistry._version_gt("2026.02.1", "2026.01.1") is True
    assert DynamoPluginRegistry._version_gt("2026.01.1", "2026.02.1") is False
    assert DynamoPluginRegistry._version_gt("2026.02.2", "2026.02.1") is True
    assert DynamoPluginRegistry._version_gt("2026.02.1", "2026.02.1") is False
