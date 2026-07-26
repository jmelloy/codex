"""Tests for the S3 sync journal + change feed API (issue #541)."""


def _sync_url(workspace):
    """Build the nested sync URL for a workspace."""
    return f"/api/v1/workspaces/{workspace['slug']}/sync"


def _push_complete(test_client, workspace, notebook, headers, *, path="foo.md", version="v1", op="created"):
    return test_client.post(
        f"{_sync_url(workspace)}/push-complete",
        json={
            "notebook_slug": notebook["slug"],
            "path": path,
            "s3_version_id": version,
            "op": op,
        },
        headers=headers,
    )


def test_push_complete_records_journal_entry(test_client, auth_headers, workspace_and_notebook):
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    response = _push_complete(test_client, workspace, notebook, headers)
    assert response.status_code == 200
    entry = response.json()
    assert entry["ws_id"] == workspace["id"]
    assert entry["nb_id"] == notebook["id"]
    assert entry["path"] == "foo.md"
    assert entry["s3_version_id"] == "v1"
    assert entry["op"] == "created"
    assert entry["actor_principal_id"] is not None
    assert entry["id"] is not None
    assert entry["ts"] is not None


def test_push_complete_rejects_invalid_op(test_client, auth_headers, workspace_and_notebook):
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    response = _push_complete(test_client, workspace, notebook, headers, op="renamed")
    assert response.status_code == 400


def test_push_complete_rejects_unknown_notebook(test_client, auth_headers, create_workspace):
    headers = auth_headers[0]
    workspace = create_workspace()

    response = test_client.post(
        f"{_sync_url(workspace)}/push-complete",
        json={"notebook_slug": "no-such-notebook", "path": "foo.md", "s3_version_id": "v1", "op": "created"},
        headers=headers,
    )
    assert response.status_code == 404


def test_push_complete_deduplicates_on_path_and_version(test_client, auth_headers, workspace_and_notebook):
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    first = _push_complete(test_client, workspace, notebook, headers, path="dup.md", version="v1")
    second = _push_complete(test_client, workspace, notebook, headers, path="dup.md", version="v1")
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]

    changes = test_client.get(f"{_sync_url(workspace)}/changes", headers=headers)
    assert changes.status_code == 200
    matching = [c for c in changes.json()["changes"] if c["path"] == "dup.md"]
    assert len(matching) == 1


def test_push_complete_same_path_different_version_is_not_deduped(test_client, auth_headers, workspace_and_notebook):
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    first = _push_complete(test_client, workspace, notebook, headers, path="revised.md", version="v1")
    second = _push_complete(test_client, workspace, notebook, headers, path="revised.md", version="v2")
    assert first.json()["id"] != second.json()["id"]


def test_push_complete_requires_authentication(test_client):
    response = test_client.post(
        "/api/v1/workspaces/no-such-ws/sync/push-complete",
        json={"notebook_slug": "x", "path": "foo.md", "s3_version_id": "v1", "op": "created"},
    )
    assert response.status_code == 401


def test_get_changes_requires_authentication(test_client):
    response = test_client.get("/api/v1/workspaces/no-such-ws/sync/changes")
    assert response.status_code == 401


def test_get_changes_cursor_pagination(test_client, auth_headers, workspace_and_notebook):
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    for i in range(3):
        resp = _push_complete(test_client, workspace, notebook, headers, path=f"file{i}.md", version=f"v{i}")
        assert resp.status_code == 200

    first_page = test_client.get(f"{_sync_url(workspace)}/changes", headers=headers, params={"since": 0, "limit": 2})
    assert first_page.status_code == 200
    body = first_page.json()
    assert len(body["changes"]) == 2
    assert body["changes"][0]["path"] == "file0.md"
    assert body["changes"][1]["path"] == "file1.md"
    cursor = body["cursor"]
    assert cursor == body["changes"][-1]["id"]

    second_page = test_client.get(f"{_sync_url(workspace)}/changes", headers=headers, params={"since": cursor})
    assert second_page.status_code == 200
    second_body = second_page.json()
    assert len(second_body["changes"]) == 1
    assert second_body["changes"][0]["path"] == "file2.md"

    # Polling again with the latest cursor returns nothing new, cursor unchanged.
    third_page = test_client.get(
        f"{_sync_url(workspace)}/changes", headers=headers, params={"since": second_body["cursor"]}
    )
    assert third_page.status_code == 200
    assert third_page.json() == {"changes": [], "cursor": second_body["cursor"]}


def test_get_changes_scoped_to_workspace(test_client, auth_headers, create_workspace):
    headers = auth_headers[0]
    workspace_a = create_workspace(name="Workspace A")
    workspace_b = create_workspace(name="Workspace B")

    nb_a = test_client.post(
        f"/api/v1/workspaces/{workspace_a['slug']}/notebooks/", json={"name": "NB A"}, headers=headers
    ).json()
    nb_b = test_client.post(
        f"/api/v1/workspaces/{workspace_b['slug']}/notebooks/", json={"name": "NB B"}, headers=headers
    ).json()

    _push_complete(test_client, workspace_a, nb_a, headers, path="a.md", version="v1")
    _push_complete(test_client, workspace_b, nb_b, headers, path="b.md", version="v1")

    changes_a = test_client.get(f"{_sync_url(workspace_a)}/changes", headers=headers).json()
    paths_a = [c["path"] for c in changes_a["changes"]]
    assert "a.md" in paths_a
    assert "b.md" not in paths_a


def test_push_complete_requires_sync_credentials_scope(test_client, auth_headers, workspace_and_notebook):
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    token_resp = test_client.post(
        "/api/v1/tokens/",
        json={"name": "no-sync-scope", "scopes": ["workspace:read"]},
        headers=headers,
    )
    assert token_resp.status_code == 201
    pat_headers = {"Authorization": f"Bearer {token_resp.json()['token']}"}

    response = _push_complete(test_client, workspace, notebook, pat_headers)
    assert response.status_code == 403


def test_push_complete_succeeds_with_sync_credentials_scope(test_client, auth_headers, workspace_and_notebook):
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    token_resp = test_client.post(
        "/api/v1/tokens/",
        json={"name": "sync-scope", "scopes": ["sync:credentials"]},
        headers=headers,
    )
    assert token_resp.status_code == 201
    pat_headers = {"Authorization": f"Bearer {token_resp.json()['token']}"}

    response = _push_complete(test_client, workspace, notebook, pat_headers)
    assert response.status_code == 200
<<<<<<< HEAD


def test_push_complete_rejects_parent_traversal_path(test_client, auth_headers, workspace_and_notebook):
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    response = _push_complete(test_client, workspace, notebook, headers, path="../../etc/passwd")
    assert response.status_code == 400


def test_push_complete_rejects_absolute_path(test_client, auth_headers, workspace_and_notebook):
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    response = _push_complete(test_client, workspace, notebook, headers, path="/etc/passwd")
    assert response.status_code == 400


def test_push_complete_does_not_dedupe_same_path_across_notebooks(test_client, auth_headers, create_workspace):
    """Two notebooks sharing a relative path + version string must not collide (Copilot review, PR #578)."""
    headers = auth_headers[0]
    workspace = create_workspace()

    nb_a = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/", json={"name": "NB A"}, headers=headers
    ).json()
    nb_b = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/", json={"name": "NB B"}, headers=headers
    ).json()

    first = _push_complete(test_client, workspace, nb_a, headers, path="readme.md", version="v1")
    second = _push_complete(test_client, workspace, nb_b, headers, path="readme.md", version="v1")
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] != second.json()["id"]
    assert first.json()["nb_id"] == nb_a["id"]
    assert second.json()["nb_id"] == nb_b["id"]


def test_push_complete_rejects_pat_scoped_to_other_workspace(
    test_client, auth_headers, workspace_and_notebook, create_workspace
):
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook
    other_workspace = create_workspace(name="Other Workspace")

    token_resp = test_client.post(
        "/api/v1/tokens/",
        json={"name": "scoped-to-other", "scopes": ["sync:credentials"], "workspace_id": other_workspace["id"]},
        headers=headers,
    )
    assert token_resp.status_code == 201
    pat_headers = {"Authorization": f"Bearer {token_resp.json()['token']}"}

    response = _push_complete(test_client, workspace, notebook, pat_headers)
    assert response.status_code == 403


def test_push_complete_succeeds_with_pat_scoped_to_matching_workspace(
    test_client, auth_headers, workspace_and_notebook
):
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    token_resp = test_client.post(
        "/api/v1/tokens/",
        json={"name": "scoped-to-this", "scopes": ["sync:credentials"], "workspace_id": workspace["id"]},
        headers=headers,
    )
    assert token_resp.status_code == 201
    pat_headers = {"Authorization": f"Bearer {token_resp.json()['token']}"}

    response = _push_complete(test_client, workspace, notebook, pat_headers)
    assert response.status_code == 200
=======
>>>>>>> origin/main
