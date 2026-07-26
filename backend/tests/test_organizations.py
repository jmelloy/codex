"""Tests for Organization and OrgMembership CRUD + membership management (issue #537).

Covers organization CRUD, invite/list/update-role/remove over OrgMembership,
role-gated management ("admins manage members, owners manage admins"),
last-owner protection, and bots as joinable members.
"""

import time


def _register_and_login(test_client, *, username=None):
    """Register and log in a second user, returning (headers, username, email)."""
    username = username or f"org_user_{int(time.time() * 1_000_000)}"
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
    return test_client.post(
        f"/api/v1/organizations/{org_slug}/members/",
        json={"username_or_email": username_or_email, "role": role},
        headers=headers,
    )


def _create_bot(test_client, headers, workspace_slug, display_name="Org Bot"):
    resp = test_client.post(
        f"/api/v1/workspaces/{workspace_slug}/bots",
        json={"display_name": display_name},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# --- Organization CRUD ---


def test_create_organization_creator_is_owner(test_client, auth_headers):
    headers = auth_headers[0]
    org = _create_org(test_client, headers)
    assert org["name"] == "Acme Corp"
    assert org["slug"]
    assert org["my_role"] == "owner"


def test_create_organization_slugifies_name_with_collision_suffix(test_client, auth_headers):
    headers = auth_headers[0]
    first = _create_org(test_client, headers, name="Duplicate Name")
    second = _create_org(test_client, headers, name="Duplicate Name")
    assert first["slug"] != second["slug"]
    assert second["slug"].startswith("duplicate-name")


def test_list_organizations_returns_only_mine(test_client, auth_headers):
    headers = auth_headers[0]
    org = _create_org(test_client, headers)
    other_headers, _, _ = _register_and_login(test_client)
    _create_org(test_client, other_headers, name="Someone Else's Org")

    resp = test_client.get("/api/v1/organizations/", headers=headers)
    assert resp.status_code == 200
    slugs = {o["slug"] for o in resp.json()}
    assert org["slug"] in slugs
    assert len(resp.json()) == 1


def test_get_organization_requires_membership(test_client, auth_headers):
    headers = auth_headers[0]
    org = _create_org(test_client, headers)

    stranger_headers, _, _ = _register_and_login(test_client)
    resp = test_client.get(f"/api/v1/organizations/{org['slug']}", headers=stranger_headers)
    assert resp.status_code == 404


def test_get_nonexistent_organization_returns_404(test_client, auth_headers):
    resp = test_client.get("/api/v1/organizations/does-not-exist", headers=auth_headers[0])
    assert resp.status_code == 404


def test_member_cannot_rename_organization(test_client, auth_headers):
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)
    member_headers, member_username, _ = _register_and_login(test_client)
    _invite(test_client, owner_headers, org["slug"], member_username, role="member")

    resp = test_client.patch(
        f"/api/v1/organizations/{org['slug']}", json={"name": "New Name"}, headers=member_headers
    )
    assert resp.status_code == 403


def test_admin_can_rename_organization(test_client, auth_headers):
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)
    admin_headers, admin_username, _ = _register_and_login(test_client)
    _invite(test_client, owner_headers, org["slug"], admin_username, role="admin")

    resp = test_client.patch(
        f"/api/v1/organizations/{org['slug']}", json={"name": "New Name"}, headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


def test_delete_organization_requires_owner(test_client, auth_headers):
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)
    admin_headers, admin_username, _ = _register_and_login(test_client)
    _invite(test_client, owner_headers, org["slug"], admin_username, role="admin")

    forbidden = test_client.delete(f"/api/v1/organizations/{org['slug']}", headers=admin_headers)
    assert forbidden.status_code == 403

    ok = test_client.delete(f"/api/v1/organizations/{org['slug']}", headers=owner_headers)
    assert ok.status_code == 200

    gone = test_client.get(f"/api/v1/organizations/{org['slug']}", headers=owner_headers)
    assert gone.status_code == 404


# --- Membership: invite ---


def test_owner_can_invite_member_by_username(test_client, auth_headers):
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)
    _, invitee_username, _ = _register_and_login(test_client)

    resp = _invite(test_client, owner_headers, org["slug"], invitee_username, role="member")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["username"] == invitee_username
    assert body["role"] == "member"
    assert body["is_bot"] is False


def test_owner_can_invite_member_by_email(test_client, auth_headers):
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)
    _, invitee_username, invitee_email = _register_and_login(test_client)

    resp = _invite(test_client, owner_headers, org["slug"], invitee_email, role="guest")
    assert resp.status_code == 201, resp.text
    assert resp.json()["username"] == invitee_username
    assert resp.json()["role"] == "guest"


def test_invite_unknown_user_returns_404(test_client, auth_headers):
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)

    resp = _invite(test_client, owner_headers, org["slug"], "nobody_here")
    assert resp.status_code == 404


def test_invite_invalid_role_returns_400(test_client, auth_headers):
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)
    _, invitee_username, _ = _register_and_login(test_client)

    resp = _invite(test_client, owner_headers, org["slug"], invitee_username, role="superadmin")
    assert resp.status_code == 400


def test_invite_duplicate_member_returns_400(test_client, auth_headers):
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)
    _, invitee_username, _ = _register_and_login(test_client)

    first = _invite(test_client, owner_headers, org["slug"], invitee_username)
    assert first.status_code == 201
    second = _invite(test_client, owner_headers, org["slug"], invitee_username)
    assert second.status_code == 400


def test_member_cannot_invite_others(test_client, auth_headers):
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)
    member_headers, member_username, _ = _register_and_login(test_client)
    _invite(test_client, owner_headers, org["slug"], member_username, role="member")

    _, target_username, _ = _register_and_login(test_client)
    resp = _invite(test_client, member_headers, org["slug"], target_username)
    assert resp.status_code == 403


def test_admin_can_invite_as_member_but_not_as_admin(test_client, auth_headers):
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)
    admin_headers, admin_username, _ = _register_and_login(test_client)
    _invite(test_client, owner_headers, org["slug"], admin_username, role="admin")

    _, member_target, _ = _register_and_login(test_client)
    member_resp = _invite(test_client, admin_headers, org["slug"], member_target, role="member")
    assert member_resp.status_code == 201

    _, admin_target, _ = _register_and_login(test_client)
    admin_resp = _invite(test_client, admin_headers, org["slug"], admin_target, role="admin")
    assert admin_resp.status_code == 403


def test_owner_can_invite_as_admin(test_client, auth_headers):
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)
    _, admin_target, _ = _register_and_login(test_client)

    resp = _invite(test_client, owner_headers, org["slug"], admin_target, role="admin")
    assert resp.status_code == 201
    assert resp.json()["role"] == "admin"


def test_stranger_gets_404_on_org_member_routes(test_client, auth_headers):
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)
    stranger_headers, _, _ = _register_and_login(test_client)

    resp = test_client.get(f"/api/v1/organizations/{org['slug']}/members/", headers=stranger_headers)
    assert resp.status_code == 404


# --- Membership: list ---


def test_list_members_includes_owner(test_client, auth_headers):
    owner_headers, owner_username = auth_headers
    org = _create_org(test_client, owner_headers)

    resp = test_client.get(f"/api/v1/organizations/{org['slug']}/members/", headers=owner_headers)
    assert resp.status_code == 200
    entries = {e["username"]: e for e in resp.json()}
    assert entries[owner_username]["role"] == "owner"


def test_guest_cannot_list_members(test_client, auth_headers):
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)
    guest_headers, guest_username, _ = _register_and_login(test_client)
    _invite(test_client, owner_headers, org["slug"], guest_username, role="guest")

    resp = test_client.get(f"/api/v1/organizations/{org['slug']}/members/", headers=guest_headers)
    assert resp.status_code == 403


# --- Membership: role change ---


def test_owner_can_change_member_role(test_client, auth_headers):
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)
    _, target_username, _ = _register_and_login(test_client)
    invite_resp = _invite(test_client, owner_headers, org["slug"], target_username, role="member")
    principal_id = invite_resp.json()["principal_id"]

    resp = test_client.patch(
        f"/api/v1/organizations/{org['slug']}/members/{principal_id}",
        json={"role": "admin"},
        headers=owner_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


def test_admin_cannot_change_another_admins_role(test_client, auth_headers):
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)
    admin_a_headers, admin_a_username, _ = _register_and_login(test_client)
    _invite(test_client, owner_headers, org["slug"], admin_a_username, role="admin")

    _, admin_b_username, _ = _register_and_login(test_client)
    admin_b_invite = _invite(test_client, owner_headers, org["slug"], admin_b_username, role="admin")
    admin_b_id = admin_b_invite.json()["principal_id"]

    resp = test_client.patch(
        f"/api/v1/organizations/{org['slug']}/members/{admin_b_id}",
        json={"role": "member"},
        headers=admin_a_headers,
    )
    assert resp.status_code == 403


def test_admin_can_change_member_role_to_guest(test_client, auth_headers):
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)
    admin_headers, admin_username, _ = _register_and_login(test_client)
    _invite(test_client, owner_headers, org["slug"], admin_username, role="admin")

    _, target_username, _ = _register_and_login(test_client)
    invite_resp = _invite(test_client, owner_headers, org["slug"], target_username, role="member")
    principal_id = invite_resp.json()["principal_id"]

    resp = test_client.patch(
        f"/api/v1/organizations/{org['slug']}/members/{principal_id}",
        json={"role": "guest"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "guest"


def test_admin_cannot_promote_member_to_admin(test_client, auth_headers):
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)
    admin_headers, admin_username, _ = _register_and_login(test_client)
    _invite(test_client, owner_headers, org["slug"], admin_username, role="admin")

    _, target_username, _ = _register_and_login(test_client)
    invite_resp = _invite(test_client, owner_headers, org["slug"], target_username, role="member")
    principal_id = invite_resp.json()["principal_id"]

    resp = test_client.patch(
        f"/api/v1/organizations/{org['slug']}/members/{principal_id}",
        json={"role": "admin"},
        headers=admin_headers,
    )
    assert resp.status_code == 403


def test_update_nonexistent_member_returns_404(test_client, auth_headers):
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)

    resp = test_client.patch(
        f"/api/v1/organizations/{org['slug']}/members/999999",
        json={"role": "member"},
        headers=owner_headers,
    )
    assert resp.status_code == 404


# --- Last-owner protection ---


def test_cannot_demote_last_owner(test_client, auth_headers):
    owner_headers, owner_username = auth_headers
    org = _create_org(test_client, owner_headers)

    me_resp = test_client.get("/api/v1/users/me", headers=owner_headers)
    owner_id = me_resp.json()["id"]

    resp = test_client.patch(
        f"/api/v1/organizations/{org['slug']}/members/{owner_id}",
        json={"role": "admin"},
        headers=owner_headers,
    )
    assert resp.status_code == 400


def test_can_demote_owner_when_another_owner_exists(test_client, auth_headers):
    owner_headers, owner_username = auth_headers
    org = _create_org(test_client, owner_headers)
    _, second_owner_username, _ = _register_and_login(test_client)
    invite_resp = _invite(test_client, owner_headers, org["slug"], second_owner_username, role="owner")
    second_owner_id = invite_resp.json()["principal_id"]

    resp = test_client.patch(
        f"/api/v1/organizations/{org['slug']}/members/{second_owner_id}",
        json={"role": "admin"},
        headers=owner_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


def test_cannot_remove_last_owner(test_client, auth_headers):
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)

    me_resp = test_client.get("/api/v1/users/me", headers=owner_headers)
    owner_id = me_resp.json()["id"]

    resp = test_client.delete(
        f"/api/v1/organizations/{org['slug']}/members/{owner_id}",
        headers=owner_headers,
    )
    assert resp.status_code == 400


def test_can_remove_owner_when_another_owner_exists(test_client, auth_headers):
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)
    _, second_owner_username, _ = _register_and_login(test_client)
    invite_resp = _invite(test_client, owner_headers, org["slug"], second_owner_username, role="owner")
    second_owner_id = invite_resp.json()["principal_id"]

    resp = test_client.delete(
        f"/api/v1/organizations/{org['slug']}/members/{second_owner_id}",
        headers=owner_headers,
    )
    assert resp.status_code == 200


# --- Membership: remove ---


def test_owner_can_remove_member(test_client, auth_headers):
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)
    _, target_username, _ = _register_and_login(test_client)
    invite_resp = _invite(test_client, owner_headers, org["slug"], target_username, role="member")
    principal_id = invite_resp.json()["principal_id"]

    resp = test_client.delete(
        f"/api/v1/organizations/{org['slug']}/members/{principal_id}",
        headers=owner_headers,
    )
    assert resp.status_code == 200

    list_resp = test_client.get(f"/api/v1/organizations/{org['slug']}/members/", headers=owner_headers)
    usernames = {e["username"] for e in list_resp.json()}
    assert target_username not in usernames


def test_admin_cannot_remove_another_admin(test_client, auth_headers):
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)
    admin_a_headers, admin_a_username, _ = _register_and_login(test_client)
    _invite(test_client, owner_headers, org["slug"], admin_a_username, role="admin")

    _, admin_b_username, _ = _register_and_login(test_client)
    admin_b_invite = _invite(test_client, owner_headers, org["slug"], admin_b_username, role="admin")
    admin_b_id = admin_b_invite.json()["principal_id"]

    resp = test_client.delete(
        f"/api/v1/organizations/{org['slug']}/members/{admin_b_id}",
        headers=admin_a_headers,
    )
    assert resp.status_code == 403


def test_remove_nonexistent_member_returns_404(test_client, auth_headers):
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)

    resp = test_client.delete(
        f"/api/v1/organizations/{org['slug']}/members/999999",
        headers=owner_headers,
    )
    assert resp.status_code == 404


# --- Bots as members ---


def test_bot_can_be_invited_as_member(test_client, auth_headers, create_workspace):
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)
    workspace = create_workspace()
    bot = _create_bot(test_client, owner_headers, workspace["slug"], display_name="Org Member Bot")

    resp = _invite(test_client, owner_headers, org["slug"], bot["username"], role="member")
    assert resp.status_code == 201, resp.text
    assert resp.json()["is_bot"] is True
    assert resp.json()["role"] == "member"


def test_bot_can_be_invited_as_guest(test_client, auth_headers, create_workspace):
    owner_headers = auth_headers[0]
    org = _create_org(test_client, owner_headers)
    workspace = create_workspace()
    bot = _create_bot(test_client, owner_headers, workspace["slug"], display_name="Org Guest Bot")

    resp = _invite(test_client, owner_headers, org["slug"], bot["username"], role="guest")
    assert resp.status_code == 201, resp.text
    assert resp.json()["is_bot"] is True
    assert resp.json()["role"] == "guest"
