"""Tests for plugin service API routes in the main backend."""

import hashlib
import io
import tarfile
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from codex.plugins.service_client import PluginServiceClient, RemotePlugin


@pytest.fixture
def test_manifest():
    return {
        "id": "remote-theme",
        "name": "Remote Theme",
        "version": "1.0.0",
        "type": "theme",
        "description": "A remote theme",
        "author": "Test",
    }


@pytest.fixture
def mock_remote_plugin(test_manifest):
    return RemotePlugin(
        plugin_id="remote-theme",
        name="Remote Theme",
        version="1.0.0",
        plugin_type="theme",
        description="A remote theme",
        author="Test",
        sha256="abc123" + "0" * 58,
        archive_size=1024,
        manifest=test_manifest,
    )


def test_service_catalog_no_client(test_client, auth_headers):
    """Test that /service/catalog returns 503 when no client is configured."""
    headers = auth_headers[0]
    response = test_client.get("/api/v1/plugins/service/catalog", headers=headers)
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_service_install_no_client(test_client, auth_headers):
    """Test that /service/install returns 503 when no client is configured."""
    headers = auth_headers[0]
    response = test_client.post(
        "/api/v1/plugins/service/install",
        json={"plugin_id": "test"},
        headers=headers,
    )
    assert response.status_code == 503


def test_service_sync_no_client(test_client, auth_headers):
    """Test that /service/sync returns 503 when no client is configured."""
    headers = auth_headers[0]
    response = test_client.post("/api/v1/plugins/service/sync", headers=headers)
    assert response.status_code == 503


def test_service_catalog_unauthorized(test_client):
    """Test that /service/catalog requires authentication."""
    response = test_client.get("/api/v1/plugins/service/catalog")
    assert response.status_code == 401


def test_service_install_unauthorized(test_client):
    """Test that /service/install requires authentication."""
    response = test_client.post(
        "/api/v1/plugins/service/install",
        json={"plugin_id": "test"},
    )
    assert response.status_code == 401


def test_service_sync_unauthorized(test_client):
    """Test that /service/sync requires authentication."""
    response = test_client.post("/api/v1/plugins/service/sync")
    assert response.status_code == 401
