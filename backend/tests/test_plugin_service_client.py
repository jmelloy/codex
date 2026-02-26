"""Tests for the plugin service client (download and verification)."""

import hashlib
import io
import json
import tarfile
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import yaml

from codex.plugins.service_client import (
    PluginServiceClient,
    PluginVerificationError,
    RemotePlugin,
)

# Dummy request object for httpx.Response (required for raise_for_status)
_DUMMY_REQUEST = httpx.Request("GET", "http://test")


def _make_response(status_code=200, json=None, content=None, headers=None):
    """Create an httpx.Response with a request object attached."""
    return httpx.Response(
        status_code,
        json=json,
        content=content,
        headers=headers or {},
        request=_DUMMY_REQUEST,
    )


def _build_test_archive(plugin_id: str, manifest: dict) -> bytes:
    """Build a tar.gz archive with a manifest for testing."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        manifest_bytes = yaml.dump(manifest).encode()
        info = tarfile.TarInfo(name=f"{plugin_id}/manifest.yml")
        info.size = len(manifest_bytes)
        tar.addfile(info, io.BytesIO(manifest_bytes))
    return buf.getvalue()


@pytest.fixture
def test_manifest():
    return {
        "id": "test-plugin",
        "name": "Test Plugin",
        "version": "1.0.0",
        "type": "theme",
        "description": "A test plugin",
        "author": "Test",
    }


@pytest.fixture
def test_archive(test_manifest):
    return _build_test_archive("test-plugin", test_manifest)


@pytest.fixture
def test_sha256(test_archive):
    return hashlib.sha256(test_archive).hexdigest()


@pytest.fixture
def plugins_dir(tmp_path):
    return tmp_path / "plugins"


@pytest.fixture
def client(plugins_dir):
    plugins_dir.mkdir(parents=True, exist_ok=True)
    return PluginServiceClient(
        service_url="http://plugin-service:8090",
        plugins_dir=plugins_dir,
    )


def test_verify_archive_success(test_archive, test_sha256):
    """Test that verification passes with correct checksum."""
    assert PluginServiceClient.verify_archive(test_archive, test_sha256) is True


def test_verify_archive_failure(test_archive):
    """Test that verification fails with wrong checksum."""
    wrong_sha256 = "a" * 64
    assert PluginServiceClient.verify_archive(test_archive, wrong_sha256) is False


def test_verify_archive_corrupted():
    """Test that verification fails with corrupted data."""
    data = b"not a valid archive"
    sha256 = hashlib.sha256(b"something else").hexdigest()
    assert PluginServiceClient.verify_archive(data, sha256) is False


@pytest.mark.asyncio
async def test_fetch_catalog(client, test_manifest, test_sha256):
    """Test fetching the plugin catalog."""
    catalog_response = {
        "plugins": [
            {
                "id": "test-plugin",
                "name": "Test Plugin",
                "version": "1.0.0",
                "type": "theme",
                "description": "A test plugin",
                "author": "Test",
                "sha256": test_sha256,
                "archive_size": 1024,
                "manifest": test_manifest,
            }
        ],
        "total": 1,
    }

    mock_response = _make_response(json=catalog_response)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        result = await client.fetch_catalog()

    assert len(result) == 1
    assert result[0].plugin_id == "test-plugin"
    assert result[0].sha256 == test_sha256


@pytest.mark.asyncio
async def test_get_plugin_info(client, test_manifest, test_sha256):
    """Test fetching info for a specific plugin."""
    info_response = {
        "id": "test-plugin",
        "name": "Test Plugin",
        "version": "1.0.0",
        "type": "theme",
        "description": "A test plugin",
        "author": "Test",
        "sha256": test_sha256,
        "archive_size": 1024,
        "manifest": test_manifest,
    }

    mock_response = _make_response(json=info_response)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        result = await client.get_plugin_info("test-plugin")

    assert result.plugin_id == "test-plugin"
    assert result.version == "1.0.0"
    assert result.sha256 == test_sha256


@pytest.mark.asyncio
async def test_download_and_verify_success(client, test_archive, test_sha256, test_manifest):
    """Test successful download and verification."""
    info_response = _make_response(json={
        "id": "test-plugin",
        "name": "Test Plugin",
        "version": "1.0.0",
        "type": "theme",
        "sha256": test_sha256,
        "archive_size": len(test_archive),
        "manifest": test_manifest,
    })

    download_response = _make_response(
        content=test_archive,
        headers={"x-checksum-sha256": test_sha256},
    )

    async def mock_get(url, **kwargs):
        if "/download" in url:
            return download_response
        return info_response

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=mock_get):
        result = await client.download_and_verify("test-plugin", test_sha256)

    assert result == test_archive


@pytest.mark.asyncio
async def test_download_and_verify_checksum_mismatch(client, test_archive, test_manifest):
    """Test that checksum mismatch raises PluginVerificationError."""
    wrong_sha256 = "a" * 64

    download_response = _make_response(
        content=test_archive,
        headers={"x-checksum-sha256": wrong_sha256},
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=download_response):
        with pytest.raises(PluginVerificationError, match="does not match"):
            await client.download_and_verify("test-plugin", "b" * 64)


@pytest.mark.asyncio
async def test_download_and_verify_content_tampered(client, test_archive, test_sha256):
    """Test that tampered content is detected."""
    tampered = test_archive + b"extra data"

    download_response = _make_response(
        content=tampered,
        headers={"x-checksum-sha256": test_sha256},
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=download_response):
        with pytest.raises(PluginVerificationError, match="expected SHA-256"):
            await client.download_and_verify("test-plugin", test_sha256)


@pytest.mark.asyncio
async def test_install_plugin(client, test_archive, test_sha256, test_manifest, plugins_dir):
    """Test installing a plugin (download, verify, extract)."""
    info_response = _make_response(json={
        "id": "test-plugin",
        "name": "Test Plugin",
        "version": "1.0.0",
        "type": "theme",
        "sha256": test_sha256,
        "archive_size": len(test_archive),
        "manifest": test_manifest,
    })

    download_response = _make_response(
        content=test_archive,
        headers={"x-checksum-sha256": test_sha256},
    )

    async def mock_get(url, **kwargs):
        if "/download" in url:
            return download_response
        return info_response

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=mock_get):
        result_path = await client.install_plugin("test-plugin", test_sha256)

    assert result_path.exists()
    assert (result_path / "manifest.yml").exists()


@pytest.mark.asyncio
async def test_install_plugin_path_traversal_blocked(client, plugins_dir):
    """Test that archives with path traversal are rejected."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        info = tarfile.TarInfo(name="../../../etc/passwd")
        info.size = 4
        tar.addfile(info, io.BytesIO(b"evil"))
    evil_archive = buf.getvalue()
    evil_sha256 = hashlib.sha256(evil_archive).hexdigest()

    download_response = _make_response(
        content=evil_archive,
        headers={"x-checksum-sha256": evil_sha256},
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=download_response):
        with pytest.raises(PluginVerificationError, match="unsafe path"):
            await client.install_plugin("evil-plugin", evil_sha256)


@pytest.mark.asyncio
async def test_sync_plugins(client, test_archive, test_sha256, test_manifest, plugins_dir):
    """Test syncing plugins from the remote catalog."""
    catalog_data = {
        "plugins": [
            {
                "id": "test-plugin",
                "name": "Test Plugin",
                "version": "1.0.0",
                "type": "theme",
                "sha256": test_sha256,
                "archive_size": len(test_archive),
                "manifest": test_manifest,
            }
        ],
        "total": 1,
    }
    info_data = {
        "id": "test-plugin",
        "name": "Test Plugin",
        "version": "1.0.0",
        "type": "theme",
        "sha256": test_sha256,
        "archive_size": len(test_archive),
        "manifest": test_manifest,
    }

    async def mock_get(url, **kwargs):
        if "/download" in url:
            return _make_response(content=test_archive, headers={"x-checksum-sha256": test_sha256})
        if "/catalog/" in url:
            return _make_response(json=info_data)
        return _make_response(json=catalog_data)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=mock_get):
        result = await client.sync_plugins()

    assert "test-plugin" in result["installed"]
    assert len(result["failed"]) == 0
    assert (plugins_dir / "test-plugin" / "manifest.yml").exists()


@pytest.mark.asyncio
async def test_sync_plugins_skips_up_to_date(client, test_archive, test_sha256, test_manifest, plugins_dir):
    """Test that sync skips plugins that are already at the correct version."""
    # Pre-install the plugin
    plugin_dir = plugins_dir / "test-plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "manifest.yml").write_text(yaml.dump(test_manifest))

    catalog_data = {
        "plugins": [
            {
                "id": "test-plugin",
                "name": "Test Plugin",
                "version": "1.0.0",
                "type": "theme",
                "sha256": test_sha256,
                "archive_size": len(test_archive),
                "manifest": test_manifest,
            }
        ],
        "total": 1,
    }

    mock_response = _make_response(json=catalog_data)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        result = await client.sync_plugins()

    assert "test-plugin" in result["skipped"]
    assert len(result["installed"]) == 0
