"""Tests for OAuth flow and Google Calendar integration."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from codex.main import app


def test_oauth_connections_requires_auth():
    """Listing OAuth connections requires authentication."""
    with TestClient(app) as client:
        response = client.get("/api/v1/oauth/connections")
        assert response.status_code == 401


def test_google_authorize_requires_auth():
    """Getting Google auth URL requires authentication."""
    with TestClient(app) as client:
        response = client.get("/api/v1/oauth/google/authorize")
        assert response.status_code == 401


def test_google_callback_requires_auth():
    """Handling Google callback requires authentication."""
    with TestClient(app) as client:
        response = client.post("/api/v1/oauth/google/callback", json={"code": "test"})
        assert response.status_code == 401


def test_google_disconnect_requires_auth():
    """Disconnecting Google requires authentication."""
    with TestClient(app) as client:
        response = client.delete("/api/v1/oauth/google/disconnect")
        assert response.status_code == 401


def test_calendar_calendars_requires_auth():
    """Listing calendars requires authentication."""
    with TestClient(app) as client:
        response = client.get("/api/v1/calendar/calendars")
        assert response.status_code == 401


def test_calendar_events_requires_auth():
    """Listing events requires authentication."""
    with TestClient(app) as client:
        response = client.get("/api/v1/calendar/events")
        assert response.status_code == 401


def test_calendar_event_detail_requires_auth():
    """Getting a single event requires authentication."""
    with TestClient(app) as client:
        response = client.get("/api/v1/calendar/events/some-event-id")
        assert response.status_code == 401


def test_list_connections_empty(auth_headers, test_client):
    """List connections returns empty list when no connections exist."""
    headers = auth_headers[0]
    response = test_client.get("/api/v1/oauth/connections", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


def test_google_authorize_returns_url(auth_headers, test_client):
    """Google authorize endpoint returns an authorization URL."""
    headers = auth_headers[0]
    with patch("codex.api.routes.oauth.get_google_auth_url") as mock_url:
        mock_url.return_value = "https://accounts.google.com/o/oauth2/auth?client_id=test"
        response = test_client.get("/api/v1/oauth/google/authorize", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert data["authorization_url"].startswith("https://accounts.google.com")


def test_google_authorize_missing_config(auth_headers, test_client):
    """Google authorize fails when client config is missing."""
    headers = auth_headers[0]
    with patch("codex.api.routes.oauth.get_google_auth_url") as mock_url:
        mock_url.side_effect = ValueError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set")
        response = test_client.get("/api/v1/oauth/google/authorize", headers=headers)
        assert response.status_code == 500


def test_google_callback_success(auth_headers, test_client):
    """Google callback successfully exchanges code and creates connection."""
    headers = auth_headers[0]
    mock_token_data = {
        "access_token": "ya29.test-access-token",
        "refresh_token": "1//test-refresh-token",
        "token_expiry": None,
        "scopes": "https://www.googleapis.com/auth/calendar.readonly",
        "provider_email": "test@gmail.com",
        "provider_user_id": "123456789",
    }

    with patch("codex.api.routes.oauth.exchange_google_code") as mock_exchange:
        mock_exchange.return_value = mock_token_data
        with patch("codex.api.routes.oauth.save_oauth_connection") as mock_save:
            mock_conn = MagicMock()
            mock_conn.provider_email = "test@gmail.com"
            mock_save.return_value = mock_conn

            response = test_client.post(
                "/api/v1/oauth/google/callback",
                json={"code": "test-auth-code"},
                headers=headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["provider"] == "google"
            assert data["provider_email"] == "test@gmail.com"
            assert data["connected"] is True


def test_google_callback_invalid_code(auth_headers, test_client):
    """Google callback fails with invalid authorization code."""
    headers = auth_headers[0]
    with patch("codex.api.routes.oauth.exchange_google_code") as mock_exchange:
        mock_exchange.side_effect = Exception("Invalid code")
        response = test_client.post(
            "/api/v1/oauth/google/callback",
            json={"code": "invalid-code"},
            headers=headers,
        )
        assert response.status_code == 400


def test_google_disconnect_no_connection(auth_headers, test_client):
    """Disconnecting Google when not connected returns 404."""
    headers = auth_headers[0]
    response = test_client.delete("/api/v1/oauth/google/disconnect", headers=headers)
    assert response.status_code == 404


def test_calendar_events_no_connection(auth_headers, test_client):
    """Listing events without a Google connection returns 400."""
    headers = auth_headers[0]
    response = test_client.get("/api/v1/calendar/events", headers=headers)
    assert response.status_code == 400
    assert "connect" in response.json()["detail"].lower()


def test_calendar_calendars_no_connection(auth_headers, test_client):
    """Listing calendars without a Google connection returns 400."""
    headers = auth_headers[0]
    response = test_client.get("/api/v1/calendar/calendars", headers=headers)
    assert response.status_code == 400
    assert "connect" in response.json()["detail"].lower()


def test_token_encryption():
    """Test that OAuth token encryption/decryption round-trips correctly."""
    from codex.core.oauth import decrypt_token, encrypt_token

    original = "ya29.test-access-token-with-special-chars/+="
    encrypted = encrypt_token(original)
    assert encrypted != original
    decrypted = decrypt_token(encrypted)
    assert decrypted == original


def test_format_event():
    """Test Google Calendar event formatting."""
    from codex.core.google_calendar import _format_event

    raw_event = {
        "id": "event123",
        "summary": "Team Meeting",
        "description": "Weekly sync",
        "location": "Room 42",
        "start": {"dateTime": "2026-02-16T10:00:00-08:00"},
        "end": {"dateTime": "2026-02-16T11:00:00-08:00"},
        "status": "confirmed",
        "htmlLink": "https://calendar.google.com/event?eid=xxx",
        "creator": {"email": "creator@example.com"},
        "organizer": {"email": "org@example.com"},
        "attendees": [
            {"email": "attendee@example.com", "displayName": "Attendee", "responseStatus": "accepted"}
        ],
    }

    formatted = _format_event(raw_event)
    assert formatted["id"] == "event123"
    assert formatted["summary"] == "Team Meeting"
    assert formatted["all_day"] is False
    assert formatted["start"] == "2026-02-16T10:00:00-08:00"
    assert len(formatted["attendees"]) == 1
    assert formatted["attendees"][0]["email"] == "attendee@example.com"


def test_format_all_day_event():
    """Test formatting an all-day event."""
    from codex.core.google_calendar import _format_event

    raw_event = {
        "id": "allday123",
        "summary": "Holiday",
        "start": {"date": "2026-02-16"},
        "end": {"date": "2026-02-17"},
    }

    formatted = _format_event(raw_event)
    assert formatted["all_day"] is True
    assert formatted["start"] == "2026-02-16"
