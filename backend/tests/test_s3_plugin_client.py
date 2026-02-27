"""Tests for the S3 plugin client."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from codex.plugins.s3_client import S3PluginClient


@pytest.fixture
def plugins_dir(tmp_path):
    d = tmp_path / "plugins"
    d.mkdir()
    return d


@pytest.fixture
def cache_dir(tmp_path):
    d = tmp_path / "cache"
    d.mkdir()
    return d


@pytest.fixture
def mock_s3():
    with patch("boto3.client") as mock_client:
        s3 = MagicMock()
        mock_client.return_value = s3
        yield s3


@pytest.fixture
def client(plugins_dir, cache_dir, mock_s3):
    return S3PluginClient(
        bucket_name="test-bucket",
        plugins_dir=plugins_dir,
        cache_dir=cache_dir,
        region_name="us-east-1",
    )


def test_list_plugin_versions(client, mock_s3):
    """Test listing available plugin versions from S3."""
    paginator = MagicMock()
    mock_s3.get_paginator.return_value = paginator
    paginator.paginate.return_value = [
        {
            "CommonPrefixes": [
                {"Prefix": "test-plugin/2026.02.1.abc1234/"},
                {"Prefix": "test-plugin/2026.02.2.def5678/"},
            ]
        }
    ]

    versions = client.list_plugin_versions("test-plugin")
    assert len(versions) == 2
    assert "2026.02.2.def5678" in versions
    assert "2026.02.1.abc1234" in versions


def test_download_plugin(client, mock_s3, plugins_dir):
    """Test downloading a plugin from S3."""
    manifest = {"id": "test-plugin", "name": "Test", "version": "1.0.0", "type": "theme"}

    paginator = MagicMock()
    mock_s3.get_paginator.return_value = paginator
    paginator.paginate.return_value = [
        {
            "Contents": [
                {"Key": "test-plugin/1.0.0/manifest.yml"},
                {"Key": "test-plugin/1.0.0/styles/main.css"},
            ]
        }
    ]

    # Mock download_file to create the files
    def fake_download(bucket, key, local_path):
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        if key.endswith("manifest.yml"):
            Path(local_path).write_text(yaml.dump(manifest))
        else:
            Path(local_path).write_text("body { color: red; }")

    mock_s3.download_file.side_effect = fake_download

    result = client.download_plugin("test-plugin", "1.0.0")
    assert result.exists()
    assert (result / "manifest.yml").exists()
    assert (result / "styles" / "main.css").exists()


def test_download_plugin_caching(client, mock_s3, plugins_dir, cache_dir):
    """Test that cached plugins are not re-downloaded."""
    # Create cache marker and plugin directory
    plugin_dir = plugins_dir / "test-plugin"
    plugin_dir.mkdir()
    (plugin_dir / "manifest.yml").write_text("id: test-plugin")
    (cache_dir / "test-plugin-1.0.0.cached").write_text("1.0.0")

    result = client.download_plugin("test-plugin", "1.0.0")
    assert result == plugin_dir
    # S3 should not have been called
    mock_s3.download_file.assert_not_called()


def test_get_manifest(client, mock_s3):
    """Test downloading and parsing a plugin manifest."""
    manifest = {"id": "test-plugin", "name": "Test", "version": "1.0.0", "type": "theme"}

    mock_s3.get_object.return_value = {
        "Body": MagicMock(read=MagicMock(return_value=yaml.dump(manifest).encode()))
    }

    result = client.get_manifest("test-plugin", "1.0.0")
    assert result["id"] == "test-plugin"
    assert result["version"] == "1.0.0"


def test_get_manifest_not_found(client, mock_s3):
    """Test that missing manifests return None."""
    from botocore.exceptions import ClientError

    mock_s3.get_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "Not found"}}, "GetObject"
    )

    result = client.get_manifest("nonexistent", "1.0.0")
    assert result is None


def test_invalidate_cache(client, cache_dir):
    """Test cache invalidation."""
    # Create some cache markers
    (cache_dir / "plugin-a-1.0.0.cached").write_text("1.0.0")
    (cache_dir / "plugin-a-2.0.0.cached").write_text("2.0.0")
    (cache_dir / "plugin-b-1.0.0.cached").write_text("1.0.0")

    # Invalidate specific plugin
    client.invalidate_cache("plugin-a")
    assert not (cache_dir / "plugin-a-1.0.0.cached").exists()
    assert not (cache_dir / "plugin-a-2.0.0.cached").exists()
    assert (cache_dir / "plugin-b-1.0.0.cached").exists()


def test_invalidate_all_cache(client, cache_dir):
    """Test invalidating all cache entries."""
    (cache_dir / "plugin-a-1.0.0.cached").write_text("1.0.0")
    (cache_dir / "plugin-b-1.0.0.cached").write_text("1.0.0")

    client.invalidate_cache()
    assert not list(cache_dir.glob("*.cached"))


def test_sync_plugin_already_cached(client, mock_s3, plugins_dir, cache_dir):
    """Test sync_plugin returns early when already cached."""
    plugin_dir = plugins_dir / "test-plugin"
    plugin_dir.mkdir()
    (cache_dir / "test-plugin-1.0.0.cached").write_text("1.0.0")

    result = client.sync_plugin("test-plugin", "1.0.0")
    assert result == plugin_dir
    mock_s3.download_file.assert_not_called()
