"""Integration tests: workspace permission levels enforced end-to-end through the API routes.

Covers issue #525's acceptance criteria - a second user granted read/write/admin on a
workspace they don't own, exercising the actual HTTP routes (not just the resolver).
"""

import asyncio
import time

from sqlmodel import select

from codex.db.database import async_session_maker
from codex.db.models import User, WorkspacePermission


def _register_and_login(test_client, *, username=None):
    """Register and log in a second user, returning (headers, username)."""
    username = username or f"perm_user_{int(time.time() * 1_000_000)}"
    test_client.post(
        "/api/v1/users/register",
        json={"username": username, "email": f"{username}@example.com", "password": "testpass123"},
    )
    login_response = test_client.post("/api/v1/users/token", data={"username": username, "password": "testpass123"})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, username


def _grant(*, workspace_id: int, username: str, level: str):
    """Grant `username` `level` access to `workspace_id` directly via the DB.

    There's no permission-management endpoint yet, so grants are seeded directly.
    """

    async def _do_grant():
        async with async_session_maker() as session:
            result = await session.execute(select(User).where(User.username == username))
            user = result.scalar_one()
            session.add(WorkspacePermission(workspace_id=workspace_id, user_id=user.id, permission_level=level))
            await session.commit()

    asyncio.run(_do_grant())


def test_list_workspaces_includes_shared_workspace(test_client, auth_headers, create_workspace):
    """A user granted access sees the workspace in their list, not just owned ones."""
    workspace = create_workspace()
    collaborator_headers, collaborator_username = _register_and_login(test_client)
    _grant(workspace_id=workspace["id"], username=collaborator_username, level="read")

    response = test_client.get("/api/v1/workspaces/", headers=collaborator_headers)
    assert response.status_code == 200
    slugs = {w["slug"] for w in response.json()}
    assert workspace["slug"] in slugs


def test_stranger_gets_404_on_shared_endpoints(test_client, auth_headers, create_workspace):
    """A user with no grant at all gets 404 (existence isn't leaked), not 403."""
    workspace = create_workspace()
    stranger_headers, _ = _register_and_login(test_client)

    response = test_client.get(f"/api/v1/workspaces/{workspace['slug']}", headers=stranger_headers)
    assert response.status_code == 404


def test_read_permission_can_view_but_not_mutate(test_client, auth_headers, create_workspace):
    """A read-level collaborator can view the workspace but is rejected on writes."""
    workspace = create_workspace()
    reader_headers, reader_username = _register_and_login(test_client)
    _grant(workspace_id=workspace["id"], username=reader_username, level="read")

    get_response = test_client.get(f"/api/v1/workspaces/{workspace['slug']}", headers=reader_headers)
    assert get_response.status_code == 200

    search_response = test_client.get(f"/api/v1/workspaces/{workspace['slug']}/search/?q=test", headers=reader_headers)
    assert search_response.status_code == 200

    create_notebook_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/",
        json={"name": "Should Not Be Created"},
        headers=reader_headers,
    )
    assert create_notebook_response.status_code == 403

    theme_response = test_client.patch(
        f"/api/v1/workspaces/{workspace['slug']}/theme", json={"theme": "dark"}, headers=reader_headers
    )
    assert theme_response.status_code == 403


def test_write_permission_can_mutate_but_not_delete(test_client, auth_headers, create_workspace):
    """A write-level collaborator can create content but cannot delete the workspace (admin-only)."""
    workspace = create_workspace()
    writer_headers, writer_username = _register_and_login(test_client)
    _grant(workspace_id=workspace["id"], username=writer_username, level="write")

    create_notebook_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/",
        json={"name": "Created By Writer"},
        headers=writer_headers,
    )
    assert create_notebook_response.status_code == 200

    delete_response = test_client.delete(f"/api/v1/workspaces/{workspace['slug']}", headers=writer_headers)
    assert delete_response.status_code == 403


def test_admin_permission_can_delete_workspace(test_client, auth_headers, create_workspace, cleanup_workspaces):
    """An admin-level collaborator (not the owner) can delete the workspace."""
    workspace = create_workspace()
    cleanup_workspaces(workspace["path"])
    admin_headers, admin_username = _register_and_login(test_client)
    _grant(workspace_id=workspace["id"], username=admin_username, level="admin")

    delete_response = test_client.delete(f"/api/v1/workspaces/{workspace['slug']}", headers=admin_headers)
    assert delete_response.status_code == 200
