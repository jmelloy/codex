"""Tests for the S3 sync credential vendor (issue #540): STS credentials + presign fallback."""

import time

import pytest

from codex.core import sync_credentials
from codex.db.models import Workspace

# ── Unit tests: pure helpers ─────────────────────────────────────────


def test_build_workspace_prefix_personal_workspace():
    workspace = Workspace(id=5, owner_id=7, name="ws", slug="ws", path="ws")
    assert sync_credentials.build_workspace_prefix(workspace) == "users/7/workspaces/5/"


def test_build_workspace_prefix_org_workspace():
    workspace = Workspace(id=5, owner_id=7, org_id=3, name="ws", slug="ws", path="ws")
    assert sync_credentials.build_workspace_prefix(workspace) == "orgs/3/workspaces/5/"


def test_build_session_policy_read_only_excludes_write_actions():
    policy = sync_credentials.build_session_policy("my-bucket", "users/1/workspaces/2/", write=False)
    actions = policy["Statement"][0]["Action"]
    assert "s3:GetObject" in actions
    assert "s3:PutObject" not in actions
    assert "s3:DeleteObject" not in actions


def test_build_session_policy_write_includes_write_actions():
    policy = sync_credentials.build_session_policy("my-bucket", "users/1/workspaces/2/", write=True)
    actions = policy["Statement"][0]["Action"]
    assert "s3:PutObject" in actions
    assert "s3:DeleteObject" in actions


def test_build_session_policy_scopes_resource_to_prefix():
    policy = sync_credentials.build_session_policy("my-bucket", "orgs/3/workspaces/5/", write=False)
    object_stmt, list_stmt = policy["Statement"]
    assert object_stmt["Resource"] == "arn:aws:s3:::my-bucket/orgs/3/workspaces/5/*"
    assert list_stmt["Resource"] == "arn:aws:s3:::my-bucket"
    assert list_stmt["Condition"]["StringLike"]["s3:prefix"] == ["orgs/3/workspaces/5/*"]


def test_resolve_key_joins_relative_key_onto_prefix():
    assert sync_credentials._resolve_key("users/1/workspaces/2/", "notes/a.md") == "users/1/workspaces/2/notes/a.md"


def test_resolve_key_empty_key_returns_prefix():
    assert sync_credentials._resolve_key("users/1/workspaces/2/", "") == "users/1/workspaces/2/"


@pytest.mark.parametrize("escape_attempt", ["../../etc/passwd", "..", "a/../../b"])
def test_resolve_key_rejects_escape_attempts(escape_attempt):
    with pytest.raises(ValueError):
        sync_credentials._resolve_key("users/1/workspaces/2/", escape_attempt)


def test_resolve_key_strips_leading_slash_without_escaping():
    # A leading "/" is stripped before the escape check, so "/etc/passwd" is treated
    # as the relative key "etc/passwd" scoped under the prefix, not an absolute path.
    assert sync_credentials._resolve_key("users/1/workspaces/2/", "/etc/passwd") == "users/1/workspaces/2/etc/passwd"


def test_is_sts_configured_requires_role_arn_and_bucket(monkeypatch):
    monkeypatch.setattr(sync_credentials, "SYNC_ROLE_ARN", None)
    monkeypatch.setattr(sync_credentials, "S3_BUCKET", "my-bucket")
    assert sync_credentials.is_sts_configured() is False

    monkeypatch.setattr(sync_credentials, "SYNC_ROLE_ARN", "arn:aws:iam::123:role/sync")
    assert sync_credentials.is_sts_configured() is True

    monkeypatch.setattr(sync_credentials, "S3_BUCKET", None)
    assert sync_credentials.is_sts_configured() is False


# ── Unit tests: generate_presigned_batch (mocked S3 client) ─────────


class _FakeS3Client:
    def generate_presigned_url(self, client_method, Params, ExpiresIn):  # noqa: N803 (matches boto3's signature)
        key_or_prefix = Params.get("Key") or Params.get("Prefix")
        return f"https://s3.example.com/{Params['Bucket']}/{key_or_prefix}?method={client_method}&exp={ExpiresIn}"


@pytest.fixture
def workspace():
    return Workspace(id=5, owner_id=7, name="ws", slug="ws", path="ws")


def test_generate_presigned_batch_requires_bucket_configured(monkeypatch, workspace):
    monkeypatch.setattr(sync_credentials, "S3_BUCKET", None)
    with pytest.raises(RuntimeError):
        sync_credentials.generate_presigned_batch(workspace, [("a.md", "get")])


def test_generate_presigned_batch_returns_bucket_prefix_and_results(monkeypatch, workspace):
    monkeypatch.setattr(sync_credentials, "S3_BUCKET", "my-bucket")
    monkeypatch.setattr(sync_credentials, "get_s3_client", lambda: _FakeS3Client())

    bucket, prefix, results = sync_credentials.generate_presigned_batch(
        workspace, [("notes/a.md", "get"), ("notes/b.md", "put")]
    )

    assert bucket == "my-bucket"
    assert prefix == "users/7/workspaces/5/"
    assert len(results) == 2

    get_result, put_result = results
    assert get_result["key"] == "notes/a.md"
    assert get_result["operation"] == "get"
    assert get_result["method"] == "GET"
    assert "users/7/workspaces/5/notes/a.md" in get_result["url"]

    assert put_result["key"] == "notes/b.md"
    assert put_result["method"] == "PUT"


def test_generate_presigned_batch_list_uses_prefix_param(monkeypatch, workspace):
    monkeypatch.setattr(sync_credentials, "S3_BUCKET", "my-bucket")
    monkeypatch.setattr(sync_credentials, "get_s3_client", lambda: _FakeS3Client())

    _bucket, prefix, results = sync_credentials.generate_presigned_batch(workspace, [("", "list")])
    assert results[0]["operation"] == "list"
    assert prefix in results[0]["url"]


def test_generate_presigned_batch_rejects_unknown_operation(monkeypatch, workspace):
    monkeypatch.setattr(sync_credentials, "S3_BUCKET", "my-bucket")
    monkeypatch.setattr(sync_credentials, "get_s3_client", lambda: _FakeS3Client())

    with pytest.raises(ValueError):
        sync_credentials.generate_presigned_batch(workspace, [("a.md", "copy")])


def test_generate_presigned_batch_rejects_key_escape(monkeypatch, workspace):
    monkeypatch.setattr(sync_credentials, "S3_BUCKET", "my-bucket")
    monkeypatch.setattr(sync_credentials, "get_s3_client", lambda: _FakeS3Client())

    with pytest.raises(ValueError):
        sync_credentials.generate_presigned_batch(workspace, [("../../secrets", "get")])


# ── Unit tests: vend_sts_credentials (mocked STS client) ─────────────


class _FakeSTSClient:
    def __init__(self, response=None, error=None):
        self._response = response
        self._error = error
        self.calls = []

    def assume_role(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        return self._response


def _fake_sts_response():
    import datetime

    return {
        "Credentials": {
            "AccessKeyId": "AKIAFAKE",
            "SecretAccessKey": "secret",
            "SessionToken": "token",
            "Expiration": datetime.datetime(2030, 1, 1, tzinfo=datetime.UTC),
        }
    }


def test_vend_sts_credentials_requires_configuration(monkeypatch, workspace):
    monkeypatch.setattr(sync_credentials, "SYNC_ROLE_ARN", None)
    with pytest.raises(RuntimeError):
        sync_credentials.vend_sts_credentials(workspace, write=False)


def test_vend_sts_credentials_happy_path(monkeypatch, workspace):
    monkeypatch.setattr(sync_credentials, "SYNC_ROLE_ARN", "arn:aws:iam::123:role/sync")
    monkeypatch.setattr(sync_credentials, "S3_BUCKET", "my-bucket")
    fake_client = _FakeSTSClient(response=_fake_sts_response())
    monkeypatch.setattr(sync_credentials, "_get_sts_client", lambda: fake_client)

    creds = sync_credentials.vend_sts_credentials(workspace, write=True)

    assert creds["access_key_id"] == "AKIAFAKE"
    assert creds["bucket"] == "my-bucket"
    assert creds["prefix"] == "users/7/workspaces/5/"

    call = fake_client.calls[0]
    assert call["RoleArn"] == "arn:aws:iam::123:role/sync"
    policy = call["Policy"]
    assert "s3:PutObject" in policy


def test_vend_sts_credentials_includes_external_id_when_set(monkeypatch, workspace):
    monkeypatch.setattr(sync_credentials, "SYNC_ROLE_ARN", "arn:aws:iam::123:role/sync")
    monkeypatch.setattr(sync_credentials, "S3_BUCKET", "my-bucket")
    monkeypatch.setattr(sync_credentials, "SYNC_EXTERNAL_ID", "ext-id-123")
    fake_client = _FakeSTSClient(response=_fake_sts_response())
    monkeypatch.setattr(sync_credentials, "_get_sts_client", lambda: fake_client)

    sync_credentials.vend_sts_credentials(workspace, write=False)

    assert fake_client.calls[0]["ExternalId"] == "ext-id-123"


def test_vend_sts_credentials_wraps_client_error(monkeypatch, workspace):
    from botocore.exceptions import ClientError

    monkeypatch.setattr(sync_credentials, "SYNC_ROLE_ARN", "arn:aws:iam::123:role/sync")
    monkeypatch.setattr(sync_credentials, "S3_BUCKET", "my-bucket")
    error = ClientError({"Error": {"Code": "AccessDenied", "Message": "nope"}}, "AssumeRole")
    fake_client = _FakeSTSClient(error=error)
    monkeypatch.setattr(sync_credentials, "_get_sts_client", lambda: fake_client)

    with pytest.raises(RuntimeError):
        sync_credentials.vend_sts_credentials(workspace, write=False)


# ── API tests: /sync/credentials and /sync/presign ───────────────────


@pytest.fixture
def owner_and_workspace(test_client, auth_headers, create_workspace):
    """Owner headers + a workspace they created."""
    headers = auth_headers[0]
    workspace = create_workspace()
    return headers, workspace


class TestCredentialsEndpoint:
    def test_returns_501_when_sts_not_configured(self, test_client, owner_and_workspace, monkeypatch):
        headers, workspace = owner_and_workspace
        monkeypatch.setattr("codex.api.routes.sync.is_sts_configured", lambda: False)

        resp = test_client.post(
            f"/api/v1/workspaces/{workspace['slug']}/sync/credentials",
            json={"write": False},
            headers=headers,
        )
        assert resp.status_code == 501

    def test_stranger_gets_404(self, test_client, owner_and_workspace):
        _, workspace = owner_and_workspace

        # Register a genuinely distinct user with no grant on this workspace.
        username = f"stranger_{int(time.time() * 1000)}"
        test_client.post(
            "/api/v1/users/register",
            json={"username": username, "email": f"{username}@example.com", "password": "testpass123"},
        )
        login = test_client.post("/api/v1/users/token", data={"username": username, "password": "testpass123"})
        stranger_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        resp = test_client.post(
            f"/api/v1/workspaces/{workspace['slug']}/sync/credentials",
            json={"write": False},
            headers=stranger_headers,
        )
        assert resp.status_code == 404

    def test_happy_path_returns_scoped_credentials(self, test_client, owner_and_workspace, monkeypatch):
        headers, workspace = owner_and_workspace
        monkeypatch.setattr("codex.api.routes.sync.is_sts_configured", lambda: True)

        import datetime

        fake_creds = {
            "access_key_id": "AKIAFAKE",
            "secret_access_key": "secret",
            "session_token": "token",
            "expiration": datetime.datetime(2030, 1, 1, tzinfo=datetime.UTC),
            "bucket": "my-bucket",
            "prefix": f"users/1/workspaces/{workspace['id']}/",
            "region": "us-east-1",
            "endpoint_url": None,
        }
        monkeypatch.setattr("codex.api.routes.sync.vend_sts_credentials", lambda ws, write: fake_creds)

        resp = test_client.post(
            f"/api/v1/workspaces/{workspace['slug']}/sync/credentials",
            json={"write": True},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["access_key_id"] == "AKIAFAKE"
        assert data["bucket"] == "my-bucket"
        assert data["region"] == "us-east-1"

    def test_vend_runtime_error_returns_502(self, test_client, owner_and_workspace, monkeypatch):
        headers, workspace = owner_and_workspace
        monkeypatch.setattr("codex.api.routes.sync.is_sts_configured", lambda: True)

        def _boom(ws, write):
            raise RuntimeError("STS AssumeRole failed: boom")

        monkeypatch.setattr("codex.api.routes.sync.vend_sts_credentials", _boom)

        resp = test_client.post(
            f"/api/v1/workspaces/{workspace['slug']}/sync/credentials",
            json={"write": False},
            headers=headers,
        )
        assert resp.status_code == 502


class TestPresignEndpoint:
    def test_rejects_empty_items(self, test_client, owner_and_workspace):
        headers, workspace = owner_and_workspace
        resp = test_client.post(
            f"/api/v1/workspaces/{workspace['slug']}/sync/presign",
            json={"items": []},
            headers=headers,
        )
        assert resp.status_code == 400

    def test_happy_path_returns_bucket_from_function_return(self, test_client, owner_and_workspace, monkeypatch):
        headers, workspace = owner_and_workspace

        def fake_generate(ws, items):
            return (
                "my-bucket",
                f"users/1/workspaces/{ws.id}/",
                [{"key": "a.md", "operation": "get", "method": "GET", "url": "https://example.com/a.md"}],
            )

        monkeypatch.setattr("codex.api.routes.sync.generate_presigned_batch", fake_generate)

        resp = test_client.post(
            f"/api/v1/workspaces/{workspace['slug']}/sync/presign",
            json={"items": [{"key": "a.md", "operation": "get"}]},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["bucket"] == "my-bucket"
        assert data["urls"][0]["url"] == "https://example.com/a.md"

    def test_key_escape_returns_400(self, test_client, owner_and_workspace, monkeypatch):
        headers, workspace = owner_and_workspace

        def fake_generate(ws, items):
            raise ValueError("Key escapes workspace prefix: '../../etc/passwd'")

        monkeypatch.setattr("codex.api.routes.sync.generate_presigned_batch", fake_generate)

        resp = test_client.post(
            f"/api/v1/workspaces/{workspace['slug']}/sync/presign",
            json={"items": [{"key": "../../etc/passwd", "operation": "get"}]},
            headers=headers,
        )
        assert resp.status_code == 400

    def test_write_operation_requires_write_permission(self, test_client, owner_and_workspace, monkeypatch):
        """A read-only collaborator can list/get but not request a put presign URL."""
        headers, workspace = owner_and_workspace

        # Create a second user and grant them READ-only access.
        username = f"reader_{int(time.time() * 1000)}"
        test_client.post(
            "/api/v1/users/register",
            json={"username": username, "email": f"{username}@example.com", "password": "testpass123"},
        )
        login = test_client.post("/api/v1/users/token", data={"username": username, "password": "testpass123"})
        reader_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        collab_resp = test_client.post(
            f"/api/v1/workspaces/{workspace['slug']}/collaborators",
            json={"username_or_email": username, "permission_level": "read"},
            headers=headers,
        )
        assert collab_resp.status_code == 201

        monkeypatch.setattr(
            "codex.api.routes.sync.generate_presigned_batch",
            lambda ws, items: ("my-bucket", "prefix/", []),
        )

        resp = test_client.post(
            f"/api/v1/workspaces/{workspace['slug']}/sync/presign",
            json={"items": [{"key": "a.md", "operation": "put"}]},
            headers=reader_headers,
        )
        assert resp.status_code == 403

        # But a get-only batch should succeed for the reader.
        resp = test_client.post(
            f"/api/v1/workspaces/{workspace['slug']}/sync/presign",
            json={"items": [{"key": "a.md", "operation": "get"}]},
            headers=reader_headers,
        )
        assert resp.status_code == 200


class TestPatWorkspaceScopeEnforcement:
    def test_pat_missing_sync_scope_is_rejected(self, test_client, owner_and_workspace):
        headers, workspace = owner_and_workspace
        token_resp = test_client.post(
            "/api/v1/tokens/",
            json={"name": "no-sync-scope", "scopes": ["workspace:read"]},
            headers=headers,
        )
        assert token_resp.status_code == 201
        pat = token_resp.json()["token"]

        resp = test_client.post(
            f"/api/v1/workspaces/{workspace['slug']}/sync/presign",
            json={"items": [{"key": "a.md", "operation": "get"}]},
            headers={"Authorization": f"Bearer {pat}"},
        )
        assert resp.status_code == 403

    def test_pat_scoped_to_other_workspace_is_rejected(self, test_client, owner_and_workspace, create_workspace):
        headers, workspace = owner_and_workspace
        other_workspace = create_workspace(name="Other Workspace")

        token_resp = test_client.post(
            "/api/v1/tokens/",
            json={
                "name": "scoped-to-other",
                "scopes": ["sync:credentials"],
                "workspace_id": other_workspace["id"],
            },
            headers=headers,
        )
        assert token_resp.status_code == 201
        pat = token_resp.json()["token"]

        resp = test_client.post(
            f"/api/v1/workspaces/{workspace['slug']}/sync/presign",
            json={"items": [{"key": "a.md", "operation": "get"}]},
            headers={"Authorization": f"Bearer {pat}"},
        )
        assert resp.status_code == 403

    def test_pat_scoped_to_matching_workspace_succeeds(self, test_client, owner_and_workspace, monkeypatch):
        headers, workspace = owner_and_workspace

        token_resp = test_client.post(
            "/api/v1/tokens/",
            json={
                "name": "scoped-to-this",
                "scopes": ["sync:credentials"],
                "workspace_id": workspace["id"],
            },
            headers=headers,
        )
        assert token_resp.status_code == 201
        pat = token_resp.json()["token"]

        monkeypatch.setattr(
            "codex.api.routes.sync.generate_presigned_batch",
            lambda ws, items: ("my-bucket", "prefix/", []),
        )

        resp = test_client.post(
            f"/api/v1/workspaces/{workspace['slug']}/sync/presign",
            json={"items": [{"key": "a.md", "operation": "get"}]},
            headers={"Authorization": f"Bearer {pat}"},
        )
        assert resp.status_code == 200
