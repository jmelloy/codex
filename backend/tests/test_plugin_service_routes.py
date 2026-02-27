"""Tests for plugin service API routes (S3/DynamoDB-based)."""

import pytest


def test_service_catalog_no_registry(test_client, auth_headers):
    """Test that /service/catalog returns 503 when no registry is configured."""
    headers = auth_headers[0]
    response = test_client.get("/api/v1/plugins/service/catalog", headers=headers)
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_service_install_no_registry(test_client, auth_headers):
    """Test that /service/install returns 503 when no registry is configured."""
    headers = auth_headers[0]
    response = test_client.post(
        "/api/v1/plugins/service/install",
        json={"plugin_id": "test"},
        headers=headers,
    )
    assert response.status_code == 503


def test_service_sync_no_registry(test_client, auth_headers):
    """Test that /service/sync returns 503 when no registry is configured."""
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
