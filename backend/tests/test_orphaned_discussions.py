"""Tests for the orphaned-discussions admin routes (design doc §4 / phase 6, issue #547).

Covers both ways a thread orphans (block hard-deleted, root soft-deleted with a live
reply), admin-only enforcement, restore/archive/delete actions, bulk actions, and the
audit log those actions write to.
"""

import time


def _register_and_login(test_client, *, username=None):
    """Register and log in a second user, returning (headers, username)."""
    username = username or f"orphan_user_{int(time.time() * 1_000_000)}"
    email = f"{username}@example.com"
    test_client.post(
        "/api/v1/users/register",
        json={"username": username, "email": email, "password": "testpass123"},
    )
    login_response = test_client.post("/api/v1/users/token", data={"username": username, "password": "testpass123"})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, username


def _create_block(test_client, headers, workspace_slug, notebook_slug, title="Discussion Page"):
    resp = test_client.post(
        f"/api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/blocks/pages",
        json={"title": title},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["block_id"]


def _delete_block(test_client, headers, workspace_slug, notebook_slug, block_id):
    resp = test_client.delete(
        f"/api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/blocks/{block_id}",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text


def _post_comment(test_client, headers, workspace_slug, notebook_slug, block_id, body, thread_id=None):
    payload = {"body": body}
    if thread_id is not None:
        payload["thread_id"] = thread_id
    resp = test_client.post(
        f"/api/v1/workspaces/{workspace_slug}/notebooks/{notebook_slug}/blocks/{block_id}/comments/",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _delete_comment(test_client, headers, comment_id):
    resp = test_client.delete(f"/api/v1/comments/{comment_id}", headers=headers)
    assert resp.status_code == 200, resp.text


def _make_block_deleted_thread(test_client, headers, workspace, notebook, body="Please review this"):
    """Create a block, post a root comment + reply on it, then delete the block."""
    block_id = _create_block(test_client, headers, workspace["slug"], notebook["slug"])
    root = _post_comment(test_client, headers, workspace["slug"], notebook["slug"], block_id, body)
    reply = _post_comment(
        test_client, headers, workspace["slug"], notebook["slug"], block_id, "A reply", thread_id=root["id"]
    )
    _delete_block(test_client, headers, workspace["slug"], notebook["slug"], block_id)
    return block_id, root, reply


def _make_root_deleted_thread(test_client, headers, workspace, notebook, body="Original question"):
    """Create a block, post a root comment + reply, then soft-delete only the root."""
    block_id = _create_block(test_client, headers, workspace["slug"], notebook["slug"])
    root = _post_comment(test_client, headers, workspace["slug"], notebook["slug"], block_id, body)
    reply = _post_comment(
        test_client, headers, workspace["slug"], notebook["slug"], block_id, "A reply", thread_id=root["id"]
    )
    _delete_comment(test_client, headers, root["id"])
    return block_id, root, reply


def _list_orphaned(test_client, headers, workspace_slug, **params):
    resp = test_client.get(
        f"/api/v1/workspaces/{workspace_slug}/orphaned-discussions/",
        headers=headers,
        params=params,
    )
    return resp


def test_block_deleted_thread_appears_as_orphaned(test_client, auth_headers, workspace_and_notebook):
    workspace, notebook = workspace_and_notebook
    owner_headers = auth_headers[0]
    _, root, _ = _make_block_deleted_thread(test_client, owner_headers, workspace, notebook)

    response = _list_orphaned(test_client, owner_headers, workspace["slug"])
    assert response.status_code == 200
    threads = response.json()
    assert len(threads) == 1
    assert threads[0]["thread_id"] == root["id"]
    assert threads[0]["reason"] == "block_deleted"
    assert threads[0]["reply_count"] == 1


def test_root_deleted_thread_with_live_reply_appears_as_orphaned(test_client, auth_headers, workspace_and_notebook):
    workspace, notebook = workspace_and_notebook
    owner_headers = auth_headers[0]
    _, root, _ = _make_root_deleted_thread(test_client, owner_headers, workspace, notebook)

    response = _list_orphaned(test_client, owner_headers, workspace["slug"])
    assert response.status_code == 200
    threads = response.json()
    assert len(threads) == 1
    assert threads[0]["thread_id"] == root["id"]
    assert threads[0]["reason"] == "root_deleted"


def test_root_deleted_with_no_live_replies_is_not_orphaned(test_client, auth_headers, workspace_and_notebook):
    """A soft-deleted root with no (live) replies is just a normal deletion, not orphaned."""
    workspace, notebook = workspace_and_notebook
    owner_headers = auth_headers[0]
    block_id = _create_block(test_client, owner_headers, workspace["slug"], notebook["slug"])
    root = _post_comment(test_client, owner_headers, workspace["slug"], notebook["slug"], block_id, "Solo comment")
    _delete_comment(test_client, owner_headers, root["id"])

    response = _list_orphaned(test_client, owner_headers, workspace["slug"])
    assert response.status_code == 200
    assert response.json() == []


def test_non_orphaned_thread_does_not_appear(test_client, auth_headers, workspace_and_notebook):
    workspace, notebook = workspace_and_notebook
    owner_headers = auth_headers[0]
    block_id = _create_block(test_client, owner_headers, workspace["slug"], notebook["slug"])
    _post_comment(test_client, owner_headers, workspace["slug"], notebook["slug"], block_id, "Still anchored")

    response = _list_orphaned(test_client, owner_headers, workspace["slug"])
    assert response.status_code == 200
    assert response.json() == []


def test_non_admin_cannot_list_orphaned_discussions(test_client, auth_headers, workspace_and_notebook):
    workspace, notebook = workspace_and_notebook
    owner_headers = auth_headers[0]
    _make_block_deleted_thread(test_client, owner_headers, workspace, notebook)

    writer_headers, writer_username = _register_and_login(test_client)
    test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/collaborators",
        json={"username_or_email": writer_username, "permission_level": "write"},
        headers=owner_headers,
    )

    response = _list_orphaned(test_client, writer_headers, workspace["slug"])
    assert response.status_code == 403


def test_stranger_gets_404_on_orphaned_discussions(test_client, auth_headers, workspace_and_notebook):
    workspace, notebook = workspace_and_notebook
    stranger_headers, _ = _register_and_login(test_client)

    response = _list_orphaned(test_client, stranger_headers, workspace["slug"])
    assert response.status_code == 404


def test_filter_by_author_id(test_client, auth_headers, workspace_and_notebook):
    workspace, notebook = workspace_and_notebook
    owner_headers, owner_username = auth_headers
    _make_block_deleted_thread(test_client, owner_headers, workspace, notebook)

    me = test_client.get("/api/v1/users/me", headers=owner_headers).json()

    matching = _list_orphaned(test_client, owner_headers, workspace["slug"], author_id=me["id"])
    assert len(matching.json()) == 1

    non_matching = _list_orphaned(test_client, owner_headers, workspace["slug"], author_id=me["id"] + 999)
    assert non_matching.json() == []


def test_restore_block_deleted_thread_requires_block_id(test_client, auth_headers, workspace_and_notebook):
    workspace, notebook = workspace_and_notebook
    owner_headers = auth_headers[0]
    _, root, _ = _make_block_deleted_thread(test_client, owner_headers, workspace, notebook)

    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/orphaned-discussions/{root['id']}/restore",
        json={},
        headers=owner_headers,
    )
    assert response.status_code == 400


def test_restore_block_deleted_thread_reanchors_to_new_block(test_client, auth_headers, workspace_and_notebook):
    workspace, notebook = workspace_and_notebook
    owner_headers = auth_headers[0]
    _, root, reply = _make_block_deleted_thread(test_client, owner_headers, workspace, notebook)
    new_block_id = _create_block(test_client, owner_headers, workspace["slug"], notebook["slug"], title="New home")

    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/orphaned-discussions/{root['id']}/restore",
        json={"block_id": new_block_id},
        headers=owner_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["block_id"] == new_block_id

    # Now anchored to a live block, so it drops out of the orphaned list...
    assert _list_orphaned(test_client, owner_headers, workspace["slug"]).json() == []

    # ...and both root and reply show up again in the normal per-block comment list.
    comments = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/blocks/{new_block_id}/comments/",
        headers=owner_headers,
    ).json()
    assert {c["id"] for c in comments} == {root["id"], reply["id"]}


def test_restore_root_deleted_thread_clears_soft_delete(test_client, auth_headers, workspace_and_notebook):
    workspace, notebook = workspace_and_notebook
    owner_headers = auth_headers[0]
    block_id, root, reply = _make_root_deleted_thread(test_client, owner_headers, workspace, notebook)

    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/orphaned-discussions/{root['id']}/restore",
        json={},
        headers=owner_headers,
    )
    assert response.status_code == 200, response.text

    assert _list_orphaned(test_client, owner_headers, workspace["slug"]).json() == []
    comments = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/blocks/{block_id}/comments/",
        headers=owner_headers,
    ).json()
    assert {c["id"] for c in comments} == {root["id"], reply["id"]}


def test_archive_thread_removes_from_default_list(test_client, auth_headers, workspace_and_notebook):
    workspace, notebook = workspace_and_notebook
    owner_headers = auth_headers[0]
    _, root, _ = _make_block_deleted_thread(test_client, owner_headers, workspace, notebook)

    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/orphaned-discussions/{root['id']}/archive",
        headers=owner_headers,
    )
    assert response.status_code == 200
    assert response.json()["archived_at"] is not None

    assert _list_orphaned(test_client, owner_headers, workspace["slug"]).json() == []

    with_archived = _list_orphaned(test_client, owner_headers, workspace["slug"], include_archived=True)
    assert len(with_archived.json()) == 1
    assert with_archived.json()[0]["thread_id"] == root["id"]


def test_delete_thread_permanently_removes_comments(test_client, auth_headers, workspace_and_notebook):
    workspace, notebook = workspace_and_notebook
    owner_headers = auth_headers[0]
    block_id, root, reply = _make_block_deleted_thread(test_client, owner_headers, workspace, notebook)

    response = test_client.delete(
        f"/api/v1/workspaces/{workspace['slug']}/orphaned-discussions/{root['id']}",
        headers=owner_headers,
    )
    assert response.status_code == 200
    assert response.json()["success"] is True

    assert _list_orphaned(test_client, owner_headers, workspace["slug"]).json() == []

    # The comment id is entirely gone now, not just soft-deleted.
    get_response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/orphaned-discussions/{root['id']}",
        headers=owner_headers,
    )
    assert get_response.status_code == 404


def test_bulk_action_archives_multiple_threads(test_client, auth_headers, workspace_and_notebook):
    workspace, notebook = workspace_and_notebook
    owner_headers = auth_headers[0]
    _, root1, _ = _make_block_deleted_thread(test_client, owner_headers, workspace, notebook, body="Thread one")
    _, root2, _ = _make_root_deleted_thread(test_client, owner_headers, workspace, notebook, body="Thread two")

    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/orphaned-discussions/bulk-action",
        json={"thread_ids": [root1["id"], root2["id"]], "action": "archive"},
        headers=owner_headers,
    )
    assert response.status_code == 200, response.text
    results = {r["thread_id"]: r for r in response.json()["results"]}
    assert results[root1["id"]]["success"] is True
    assert results[root2["id"]]["success"] is True

    assert _list_orphaned(test_client, owner_headers, workspace["slug"]).json() == []


def test_bulk_action_reports_per_thread_failure_without_aborting(test_client, auth_headers, workspace_and_notebook):
    workspace, notebook = workspace_and_notebook
    owner_headers = auth_headers[0]
    _, root, _ = _make_block_deleted_thread(test_client, owner_headers, workspace, notebook)

    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/orphaned-discussions/bulk-action",
        json={"thread_ids": [root["id"], 999999], "action": "archive"},
        headers=owner_headers,
    )
    assert response.status_code == 200
    results = {r["thread_id"]: r for r in response.json()["results"]}
    assert results[root["id"]]["success"] is True
    assert results[999999]["success"] is False


def test_audit_log_records_admin_actions(test_client, auth_headers, workspace_and_notebook):
    workspace, notebook = workspace_and_notebook
    owner_headers = auth_headers[0]
    _, root, _ = _make_block_deleted_thread(test_client, owner_headers, workspace, notebook)

    test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/orphaned-discussions/{root['id']}/archive",
        headers=owner_headers,
    )

    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/orphaned-discussions/audit-log",
        headers=owner_headers,
    )
    assert response.status_code == 200
    entries = response.json()
    assert any(e["kind"] == "comment.orphan_archived" and e["subject"]["thread_id"] == root["id"] for e in entries)
    assert entries[0]["actor_username"] is not None


def test_audit_log_requires_admin(test_client, auth_headers, workspace_and_notebook):
    workspace, notebook = workspace_and_notebook
    owner_headers = auth_headers[0]

    writer_headers, writer_username = _register_and_login(test_client)
    test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/collaborators",
        json={"username_or_email": writer_username, "permission_level": "write"},
        headers=owner_headers,
    )

    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/orphaned-discussions/audit-log",
        headers=writer_headers,
    )
    assert response.status_code == 403


def test_admin_collaborator_can_manage_orphaned_discussions(test_client, auth_headers, workspace_and_notebook):
    """Admin isn't limited to the workspace owner - a granted admin can act too."""
    workspace, notebook = workspace_and_notebook
    owner_headers = auth_headers[0]
    admin_headers, admin_username = _register_and_login(test_client)
    test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/collaborators",
        json={"username_or_email": admin_username, "permission_level": "admin"},
        headers=owner_headers,
    )
    _, root, _ = _make_block_deleted_thread(test_client, owner_headers, workspace, notebook)

    response = _list_orphaned(test_client, admin_headers, workspace["slug"])
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["thread_id"] == root["id"]


def test_get_single_orphaned_discussion_not_found_for_live_thread(test_client, auth_headers, workspace_and_notebook):
    workspace, notebook = workspace_and_notebook
    owner_headers = auth_headers[0]
    block_id = _create_block(test_client, owner_headers, workspace["slug"], notebook["slug"])
    root = _post_comment(test_client, owner_headers, workspace["slug"], notebook["slug"], block_id, "Still fine")

    response = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}/orphaned-discussions/{root['id']}",
        headers=owner_headers,
    )
    assert response.status_code == 404
