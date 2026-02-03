"""Basic tests for the API."""

from fastapi.testclient import TestClient

from codex.main import app


def test_read_root():
    """Test root endpoint."""
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()
        assert response.json()["message"] == "Codex API"


def test_docs_available():
    """Test that API docs are available."""
    with TestClient(app) as client:
        response = client.get("/docs")
        assert response.status_code == 200


def test_openapi_available():
    """Test that OpenAPI schema is available."""
    with TestClient(app) as client:
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert "openapi" in response.json()
