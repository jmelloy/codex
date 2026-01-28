"""Basic tests for the API."""

from fastapi.testclient import TestClient

from codex.main import app

client = TestClient(app)


def test_read_root():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
    assert response.json()["message"] == "Codex API"


def test_docs_available():
    """Test that API docs are available."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_available():
    """Test that OpenAPI schema is available."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "openapi" in response.json()


def test_get_themes():
    """Test themes endpoint returns available themes."""
    response = client.get("/api/v1/themes")
    assert response.status_code == 200
    
    themes = response.json()
    assert isinstance(themes, list)
    assert len(themes) >= 4  # At least 4 built-in themes
    
    # Check theme structure
    for theme in themes:
        assert "id" in theme
        assert "name" in theme
        assert "label" in theme
        assert "description" in theme
        assert "className" in theme
        assert "category" in theme
        assert "version" in theme
        assert "author" in theme
    
    # Check that known themes exist
    theme_ids = [t["id"] for t in themes]
    assert "cream" in theme_ids
    assert "manila" in theme_ids
    assert "white" in theme_ids
    assert "blueprint" in theme_ids
