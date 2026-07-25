"""Tests for collaborator management routes (issue #528).

Covers invite/list/update/revoke over the WorkspacePermission table, admin-only
enforcement via the permission resolver, and owner protections.
"""

import time


def _register_and_login(test_client, *, username=None):
    """Register and log in a second user, returning (headers, username, email)."""
    username = username or f"collab_user_{int(time.time() * 1_000_000)}"
    email = f"{username}@example.com"
    test_client.post(
        "/api/v1/users/register",
        json={"username": username, "email": email, "password": "testpass123"},
    )
    login_response = test_client.post("/api/v1/users/token", data={"username": username, "password": "testpass123"})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, username, email


def test_owner_can_invite_collaborator_by_username(test_client, auth_headers, create_workspace):
    workspace = create_workspace()
    owner_headers = auth_headers[0]
    _, collaborator_username, _ = _register_and_login(test_client)

    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/collaborators",
        json={"username_or_email": collaborator_username, "permission_level": "write"},
        headers=owner_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == collaborator_username
    assert body["permission_level"] == "write"
    assert body["is_owner"] is False


def test_owner_can_invite_collaborator_by_email(test_client, auth_headers, create_workspace):
    workspace = create_workspace()
    owner_headers = auth_headers[0]
    _, collaborator_username, collaborator_email = _register_and_login(test_client)

    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/collaborators",
        json={"username_or_email": collaborator_email, "permission_level": "read"},
        headers=owner_headers,
    )
    assert response.status_code == 201
    assert response.json()["username"] == collaborator_username


def test_invite_unknown_user_returns_404(test_client, auth_headers, create_workspace):
    workspace = create_workspace()
    owner_headers = auth_headers[0]

    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/collaborators",
        json={"username_or_email": "nobody_here", "permission_level": "read"},
        headers=owner_headers,
    )
    assert response.status_code == 404


def test_invite_invalid_permission_level_returns_400(test_client, auth_headers, create_workspace):
    workspace = create_workspace()
    owner_headers = auth_headers[0]
    _, collaborator_username, _ = _register_and_login(test_client)

    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/collaborators",
        json={"username_or_email": collaborator_username, "permission_level": "superadmin"},
        headers=owner_headers,
    )
    assert response.status_code == 400


def test_invite_duplicate_collaborator_returns_400(test_client, auth_headers, create_workspace):
    workspace = create_workspace()
    owner_headers = auth_headers[0]
    _, collaborator_username, _ = _register_and_login(test_client)

    first = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/collaborators",
        json={"username_or_email": collaborator_username, "permission_level": "read"},
        headers=owner_headers,
    )
    assert first.status_code == 201

    second = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/collaborators",
        json={"username_or_email": collaborator_username, "permission_level": "write"},
        headers=owner_headers,
    )
    assert second.status_code == 400


def test_invite_owner_returns_400(test_client, auth_headers, create_workspace):
    workspace = create_workspace()
    owner_headers, owner_username = auth_headers

    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/collaborators",
        json={"username_or_email": owner_username, "permission_level": "write"},
        headers=owner_headers,
    )
    assert response.status_code == 400


def test_list_collaborators_includes_owner_and_grants(test_client, auth_headers, create_workspace):
    workspace = create_workspace()
    owner_headers, owner_username = auth_headers
    _, collaborator_username, _ = _register_and_login(test_client)

    test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/collaborators",
        json={"username_or_email": collaborator_username, "permission_level": "comment"},
        headers=owner_headers,
    )

    response = test_client.get(f"/api/v1/workspaces/{workspace['slug']}/collaborators", headers=owner_headers)
    assert response.status_code == 200
    entries = {entry["username"]: entry for entry in response.json()}

    assert entries[owner_username]["is_owner"] is True
    assert entries[owner_username]["permission_level"] == "admin"
    assert entries[collaborator_username]["is_owner"] is False
    assert entries[collaborator_username]["permission_level"] == "comment"


def test_non_admin_cannot_list_collaborators(test_client, auth_headers, create_workspace):
    workspace = create_workspace()
    owner_headers = auth_headers[0]
    writer_headers, writer_username, _ = _register_and_login(test_client)

    test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/collaborators",
        json={"username_or_email": writer_username, "permission_level": "write"},
        headers=owner_headers,
    )

    response = test_client.get(f"/api/v1/workspaces/{workspace['slug']}/collaborators", headers=writer_headers)
    assert response.status_code == 403


def test_stranger_gets_404_on_collaborator_routes(test_client, auth_headers, create_workspace):
    workspace = create_workspace()
    stranger_headers, _, _ = _register_and_login(test_client)

    response = test_client.get(f"/api/v1/workspaces/{workspace['slug']}/collaborators", headers=stranger_headers)
    assert response.status_code == 404


def test_admin_collaborator_can_manage_others(test_client, auth_headers, create_workspace):
    workspace = create_workspace()
    owner_headers = auth_headers[0]
    admin_headers, admin_username, _ = _register_and_login(test_client)
    _, target_username, _ = _register_and_login(test_client)

    test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/collaborators",
        json={"username_or_email": admin_username, "permission_level": "admin"},
        headers=owner_headers,
    )

    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/collaborators",
        json={"username_or_email": target_username, "permission_level": "read"},
        headers=admin_headers,
    )
    assert response.status_code == 201


def test_owner_can_update_collaborator_level(test_client, auth_headers, create_workspace):
    workspace = create_workspace()
    owner_headers = auth_headers[0]
    _, collaborator_username, _ = _register_and_login(test_client)

    invite_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/collaborators",
        json={"username_or_email": collaborator_username, "permission_level": "read"},
        headers=owner_headers,
    )
    user_id = invite_response.json()["user_id"]

    update_response = test_client.patch(
        f"/api/v1/workspaces/{workspace['slug']}/collaborators/{user_id}",
        json={"permission_level": "write"},
        headers=owner_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["permission_level"] == "write"


def test_update_nonexistent_collaborator_returns_404(test_client, auth_headers, create_workspace):
    workspace = create_workspace()
    owner_headers = auth_headers[0]

    response = test_client.patch(
        f"/api/v1/workspaces/{workspace['slug']}/collaborators/999999",
        json={"permission_level": "write"},
        headers=owner_headers,
    )
    assert response.status_code == 404


def test_cannot_update_owner_permission_level(test_client, auth_headers, create_workspace):
    workspace = create_workspace()
    owner_headers, owner_username = auth_headers

    me_response = test_client.get("/api/v1/users/me", headers=owner_headers)
    owner_id = me_response.json()["id"]

    response = test_client.patch(
        f"/api/v1/workspaces/{workspace['slug']}/collaborators/{owner_id}",
        json={"permission_level": "read"},
        headers=owner_headers,
    )
    assert response.status_code == 400


def test_cannot_revoke_owner(test_client, auth_headers, create_workspace):
    workspace = create_workspace()
    owner_headers = auth_headers[0]

    me_response = test_client.get("/api/v1/users/me", headers=owner_headers)
    owner_id = me_response.json()["id"]

    response = test_client.delete(
        f"/api/v1/workspaces/{workspace['slug']}/collaborators/{owner_id}",
        headers=owner_headers,
    )
    assert response.status_code == 400


def test_owner_can_revoke_collaborator(test_client, auth_headers, create_workspace):
    workspace = create_workspace()
    owner_headers = auth_headers[0]
    collaborator_headers, collaborator_username, _ = _register_and_login(test_client)

    invite_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/collaborators",
        json={"username_or_email": collaborator_username, "permission_level": "read"},
        headers=owner_headers,
    )
    user_id = invite_response.json()["user_id"]

    delete_response = test_client.delete(
        f"/api/v1/workspaces/{workspace['slug']}/collaborators/{user_id}",
        headers=owner_headers,
    )
    assert delete_response.status_code == 200

    # Access is actually gone: the workspace now 404s for the revoked collaborator.
    get_response = test_client.get(f"/api/v1/workspaces/{workspace['slug']}", headers=collaborator_headers)
    assert get_response.status_code == 404


def test_revoke_nonexistent_collaborator_returns_404(test_client, auth_headers, create_workspace):
    workspace = create_workspace()
    owner_headers = auth_headers[0]

    response = test_client.delete(
        f"/api/v1/workspaces/{workspace['slug']}/collaborators/999999",
        headers=owner_headers,
    )
    assert response.status_code == 404
