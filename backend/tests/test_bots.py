"""Tests for bot service accounts and PAT issuance (issue #533).

Covers the acceptance criteria: create bot -> issue workspace-scoped PAT ->
bot reads workspace via API; login endpoint rejects bot credentials outright;
and is_active=false kills all bot access immediately.
"""

import time


def _register_and_login(test_client, *, username=None):
    """Register and log in a second user, returning (headers, username, email)."""
    username = username or f"bot_test_user_{int(time.time() * 1_000_000)}"
    email = f"{username}@example.com"
    test_client.post(
        "/api/v1/users/register",
        json={"username": username, "email": email, "password": "testpass123"},
    )
    login_response = test_client.post("/api/v1/users/token", data={"username": username, "password": "testpass123"})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, username, email


def _create_bot(test_client, headers, workspace_slug, display_name="CI Bot"):
    resp = test_client.post(
        f"/api/v1/workspaces/{workspace_slug}/bots",
        json={"display_name": display_name},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_bot_requires_display_name(test_client, auth_headers, create_workspace):
    workspace = create_workspace()
    resp = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/bots",
        json={"display_name": ""},
        headers=auth_headers[0],
    )
    assert resp.status_code == 422


def test_non_admin_cannot_create_bot(test_client, auth_headers, create_workspace):
    workspace = create_workspace()
    collaborator_headers, collaborator_username, _ = _register_and_login(test_client)

    test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/collaborators",
        json={"username_or_email": collaborator_username, "permission_level": "write"},
        headers=auth_headers[0],
    )

    resp = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/bots",
        json={"display_name": "Sneaky Bot"},
        headers=collaborator_headers,
    )
    assert resp.status_code == 403


def test_create_bot_and_issue_token_reads_workspace(test_client, auth_headers, create_workspace):
    """Acceptance: create bot -> issue workspace-scoped PAT -> bot reads workspace via API."""
    workspace = create_workspace()
    headers = auth_headers[0]

    bot = _create_bot(test_client, headers, workspace["slug"])
    assert bot["kind"] == "bot"
    assert bot["is_bot"] is True
    assert bot["username"] == "bot-ci-bot"
    assert bot["is_active"] is True

    token_resp = test_client.post(
        f"/api/v1/tokens/bots/{bot['id']}/tokens",
        json={"name": "prod", "workspace_id": workspace["id"]},
        headers=headers,
    )
    assert token_resp.status_code == 201, token_resp.text
    token_data = token_resp.json()
    assert token_data["token"].startswith("cdx_")
    assert token_data["workspace_id"] == workspace["id"]

    bot_headers = {"Authorization": f"Bearer {token_data['token']}"}
    get_resp = test_client.get(f"/api/v1/workspaces/{workspace['slug']}", headers=bot_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["slug"] == workspace["slug"]


def test_bot_token_rejected_for_workspace_without_grant(test_client, auth_headers, create_workspace):
    workspace_a = create_workspace(name="Workspace A")
    workspace_b = create_workspace(name="Workspace B")
    headers = auth_headers[0]

    bot = _create_bot(test_client, headers, workspace_a["slug"])

    resp = test_client.post(
        f"/api/v1/tokens/bots/{bot['id']}/tokens",
        json={"name": "cross-workspace", "workspace_id": workspace_b["id"]},
        headers=headers,
    )
    assert resp.status_code == 400


def test_bot_appears_in_collaborators_with_is_bot_flag(test_client, auth_headers, create_workspace):
    workspace = create_workspace()
    headers = auth_headers[0]
    bot = _create_bot(test_client, headers, workspace["slug"], display_name="Reviewer Bot")

    resp = test_client.get(f"/api/v1/workspaces/{workspace['slug']}/collaborators", headers=headers)
    assert resp.status_code == 200
    entry = next(e for e in resp.json() if e["user_id"] == bot["id"])
    assert entry["is_bot"] is True
    assert entry["display_name"] == "Reviewer Bot"


def test_bot_appears_in_principals_with_is_bot_flag(test_client, auth_headers, create_workspace):
    workspace = create_workspace()
    headers = auth_headers[0]
    bot = _create_bot(test_client, headers, workspace["slug"], display_name="Mention Bot")

    resp = test_client.get(f"/api/v1/workspaces/{workspace['slug']}/principals", headers=headers)
    assert resp.status_code == 200
    entry = next(e for e in resp.json() if e["id"] == bot["id"])
    assert entry["is_bot"] is True
    assert entry["display_name"] == "Mention Bot"


def test_login_rejects_bot_credentials(test_client, auth_headers, create_workspace):
    """Acceptance: login endpoint rejects bot credentials outright."""
    workspace = create_workspace()
    headers = auth_headers[0]
    bot = _create_bot(test_client, headers, workspace["slug"], display_name="Login Bot")

    resp = test_client.post(
        "/api/v1/users/token",
        data={"username": bot["username"], "password": "anything"},
    )
    assert resp.status_code == 403


def test_deactivate_bot_kills_access_immediately(test_client, auth_headers, create_workspace):
    """Acceptance: is_active=false kills all bot access immediately."""
    workspace = create_workspace()
    headers = auth_headers[0]
    bot = _create_bot(test_client, headers, workspace["slug"], display_name="Ephemeral Bot")

    token_resp = test_client.post(
        f"/api/v1/tokens/bots/{bot['id']}/tokens",
        json={"name": "main", "workspace_id": workspace["id"]},
        headers=headers,
    )
    plain_token = token_resp.json()["token"]
    bot_headers = {"Authorization": f"Bearer {plain_token}"}

    # Sanity check: bot can read the workspace before deactivation.
    assert test_client.get(f"/api/v1/workspaces/{workspace['slug']}", headers=bot_headers).status_code == 200

    deactivate_resp = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/bots/{bot['id']}/deactivate",
        headers=headers,
    )
    assert deactivate_resp.status_code == 200
    assert deactivate_resp.json()["is_active"] is False

    blocked_resp = test_client.get(f"/api/v1/workspaces/{workspace['slug']}", headers=bot_headers)
    assert blocked_resp.status_code == 401

    list_resp = test_client.get(f"/api/v1/tokens/bots/{bot['id']}/tokens", headers=headers)
    assert list_resp.status_code == 200
    assert all(t["is_active"] is False for t in list_resp.json())


def test_update_bot_profile(test_client, auth_headers, create_workspace):
    workspace = create_workspace()
    headers = auth_headers[0]
    bot = _create_bot(test_client, headers, workspace["slug"], display_name="Old Name")

    resp = test_client.patch(
        f"/api/v1/workspaces/{workspace['slug']}/bots/{bot['id']}",
        json={"display_name": "New Name", "avatar_url": "https://example.com/avatar.png"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["display_name"] == "New Name"
    assert body["avatar_url"] == "https://example.com/avatar.png"
