"""Tests for org-scoped workspace support (issue #538).

Covers `Workspace.org_id`, org-scoped slug uniqueness, the `/orgs/{org_slug}/workspaces`
routes, and the permission resolver's org-role-based implicit access (owner/admin ->
admin, member -> workspace default, guest -> explicit grants only).
"""

import uuid


def _register_and_login(test_client, *, username=None):
    username = username or f"org_ws_user_{uuid.uuid4().hex}"
    email = f"{username}@example.com"
    test_client.post(
        "/api/v1/users/register",
        json={"username": username, "email": email, "password": "testpass123"},
    )
    login_response = test_client.post("/api/v1/users/token", data={"username": username, "password": "testpass123"})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, username, email


def _create_org(test_client, headers, name="Acme Corp"):
    resp = test_client.post("/api/v1/organizations/", json={"name": name}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _invite(test_client, headers, org_slug, username_or_email, role="member"):
    resp = test_client.post(
        f"/api/v1/organizations/{org_slug}/members/",
        json={"username_or_email": username_or_email, "role": role},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_org_workspace(test_client, headers, org_slug, name="Team Space"):
    resp = test_client.post(f"/api/v1/orgs/{org_slug}/workspaces/", json={"name": name}, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_personal_workspace_org_id_is_null(test_client, auth_headers):
    """Existing personal-workspace creation is unaffected: org_id stays null."""
    headers = auth_headers[0]
    resp = test_client.post("/api/v1/workspaces/", json={"name": "Just Mine"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["org_id"] is None


def test_same_slug_allowed_in_different_orgs(test_client, auth_headers):
    """Acceptance: create workspace under an org; same slug allowed in different orgs."""
    headers = auth_headers[0]
    org1 = _create_org(test_client, headers, name="Org One")
    org2 = _create_org(test_client, headers, name="Org Two")

    ws1 = _create_org_workspace(test_client, headers, org1["slug"], name="Shared Name")
    ws2 = _create_org_workspace(test_client, headers, org2["slug"], name="Shared Name")

    assert ws1["slug"] == ws2["slug"]
    assert ws1["org_id"] == org1["id"]
    assert ws2["org_id"] == org2["id"]
    assert ws1["id"] != ws2["id"]


def test_org_workspace_slug_collision_within_same_org_gets_suffixed(test_client, auth_headers):
    headers = auth_headers[0]
    org = _create_org(test_client, headers)

    ws1 = _create_org_workspace(test_client, headers, org["slug"], name="Docs")
    ws2 = _create_org_workspace(test_client, headers, org["slug"], name="Docs")

    assert ws1["slug"] != ws2["slug"]
    assert ws2["slug"].startswith("docs")


def test_org_admin_has_implicit_admin_access_without_explicit_grant(test_client, auth_headers):
    """Acceptance: org admin has admin access without an explicit grant."""
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)
    ws = _create_org_workspace(test_client, owner_headers, org["slug"])

    admin_headers, admin_username, _ = _register_and_login(test_client)
    _invite(test_client, owner_headers, org["slug"], admin_username, role="admin")

    resp = test_client.get(f"/api/v1/orgs/{org['slug']}/workspaces/{ws['slug']}", headers=admin_headers)
    assert resp.status_code == 200

    perm_resp = test_client.get(f"/api/v1/workspaces/{ws['slug']}/permission", headers=admin_headers)
    assert perm_resp.status_code == 200
    assert perm_resp.json()["permission_level"] == "admin"

    # Admin can delete without any WorkspacePermission grant ever being created.
    delete_resp = test_client.delete(f"/api/v1/workspaces/{ws['slug']}", headers=admin_headers)
    assert delete_resp.status_code == 200


def test_org_member_gets_default_read_access(test_client, auth_headers):
    """Member role gets the workspace's configurable default level (read by default)."""
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)
    ws = _create_org_workspace(test_client, owner_headers, org["slug"])

    member_headers, member_username, _ = _register_and_login(test_client)
    _invite(test_client, owner_headers, org["slug"], member_username, role="member")

    resp = test_client.get(f"/api/v1/orgs/{org['slug']}/workspaces/{ws['slug']}", headers=member_headers)
    assert resp.status_code == 200

    perm_resp = test_client.get(f"/api/v1/workspaces/{ws['slug']}/permission", headers=member_headers)
    assert perm_resp.status_code == 200
    assert perm_resp.json()["permission_level"] == "read"

    # Read-only: a member cannot delete the workspace.
    delete_resp = test_client.delete(f"/api/v1/workspaces/{ws['slug']}", headers=member_headers)
    assert delete_resp.status_code == 403


def test_org_guest_has_no_default_access(test_client, auth_headers):
    """Acceptance: guest has none (no implicit access without an explicit grant)."""
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)
    ws = _create_org_workspace(test_client, owner_headers, org["slug"])

    guest_headers, guest_username, _ = _register_and_login(test_client)
    _invite(test_client, owner_headers, org["slug"], guest_username, role="guest")

    resp = test_client.get(f"/api/v1/orgs/{org['slug']}/workspaces/{ws['slug']}", headers=guest_headers)
    assert resp.status_code == 404

    perm_resp = test_client.get(f"/api/v1/workspaces/{ws['slug']}/permission", headers=guest_headers)
    assert perm_resp.status_code == 404


def test_list_org_workspaces_filters_by_access(test_client, auth_headers):
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)
    visible_ws = _create_org_workspace(test_client, owner_headers, org["slug"], name="Visible")
    _create_org_workspace(test_client, owner_headers, org["slug"], name="Hidden From Guest")

    guest_headers, guest_username, _ = _register_and_login(test_client)
    _invite(test_client, owner_headers, org["slug"], guest_username, role="guest")

    # Grant the guest explicit access to just one of the two workspaces.
    grant_resp = test_client.post(
        f"/api/v1/workspaces/{visible_ws['slug']}/collaborators",
        json={"username_or_email": guest_username, "permission_level": "read"},
        headers=owner_headers,
    )
    assert grant_resp.status_code in (200, 201), grant_resp.text

    resp = test_client.get(f"/api/v1/orgs/{org['slug']}/workspaces/", headers=guest_headers)
    assert resp.status_code == 200
    slugs = {w["slug"] for w in resp.json()}
    assert slugs == {visible_ws["slug"]}


def test_non_org_member_cannot_list_or_create_org_workspaces(test_client, auth_headers):
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)

    stranger_headers, _, _ = _register_and_login(test_client)

    list_resp = test_client.get(f"/api/v1/orgs/{org['slug']}/workspaces/", headers=stranger_headers)
    assert list_resp.status_code == 404

    create_resp = test_client.post(
        f"/api/v1/orgs/{org['slug']}/workspaces/", json={"name": "Nope"}, headers=stranger_headers
    )
    assert create_resp.status_code == 404


def test_org_guest_cannot_create_org_workspace(test_client, auth_headers):
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)

    guest_headers, guest_username, _ = _register_and_login(test_client)
    _invite(test_client, owner_headers, org["slug"], guest_username, role="guest")

    resp = test_client.post(f"/api/v1/orgs/{org['slug']}/workspaces/", json={"name": "Nope"}, headers=guest_headers)
    assert resp.status_code == 403
