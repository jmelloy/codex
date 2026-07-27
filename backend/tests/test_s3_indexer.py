"""Tests for the server working-copy indexer for shared notebooks (issue #542)."""

import threading
import time
from pathlib import Path

import pytest
from sqlmodel import select

from codex.core import s3_indexer
from codex.db.database import get_notebook_session, get_system_session_sync, init_notebook_db
from codex.db.models import Block, SyncJournal, Workspace
from codex.db.models import Notebook as NotebookModel


class _FakeS3:
    """In-memory S3 stand-in, following this repo's monkeypatch-fake convention
    (see test_sync_credentials.py's `_FakeS3Client`/`_FakeSTSClient`)."""

    def __init__(self):
        self.objects: dict[str, bytes] = {}
        self.versions: dict[tuple[str, str], bytes] = {}

    def put(self, key: str, data: bytes, version_id: str = "v1") -> None:
        self.objects[key] = data
        self.versions[(key, version_id)] = data

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)

    def get_paginator(self, name):
        assert name == "list_objects_v2"
        store = self

        class _Paginator:
            def paginate(self, Bucket, Prefix):  # noqa: N803 (matches boto3's signature)
                return [{"Contents": [{"Key": k} for k in store.objects if k.startswith(Prefix)]}]

        return _Paginator()


@pytest.fixture
def fake_s3(monkeypatch):
    fake = _FakeS3()
    monkeypatch.setattr(s3_indexer, "is_s3_configured", lambda: True)
    monkeypatch.setattr(s3_indexer, "S3_BUCKET", "test-bucket")
    monkeypatch.setattr(s3_indexer, "get_s3_client", lambda: fake)

    def _fake_download(s3_key, version_id=None, bucket=None):
        if version_id and (s3_key, version_id) in fake.versions:
            return fake.versions[(s3_key, version_id)]
        return fake.objects[s3_key]

    monkeypatch.setattr(s3_indexer, "download_binary", _fake_download)
    return fake


@pytest.fixture
def shared_workspace(tmp_path):
    """A plain (unpersisted) shared workspace + notebook pair, like test_sync_credentials.py's."""
    ws_path = tmp_path / "ws"
    ws_path.mkdir()
    workspace = Workspace(id=101, owner_id=1, org_id=9, name="Shared WS", slug="shared-ws", path=str(ws_path))
    notebook = NotebookModel(id=202, workspace_id=workspace.id, name="Notebook", slug="nb", path="notebook")
    return workspace, notebook


def _prefix(workspace, notebook):
    return s3_indexer.notebook_content_prefix(workspace, notebook)


# ── Pure helpers ──────────────────────────────────────────────────────


def test_is_shared_workspace_true_for_org_workspace():
    ws = Workspace(id=1, owner_id=1, org_id=3, name="w", slug="w", path="w")
    assert s3_indexer.is_shared_workspace(ws) is True


def test_is_shared_workspace_false_for_personal_workspace():
    ws = Workspace(id=1, owner_id=1, name="w", slug="w", path="w")
    assert s3_indexer.is_shared_workspace(ws) is False


def test_notebook_content_prefix_uses_org_layout():
    ws = Workspace(id=5, owner_id=7, org_id=3, name="w", slug="w", path="w")
    nb = NotebookModel(id=11, workspace_id=5, name="n", slug="n", path="n")
    assert s3_indexer.notebook_content_prefix(ws, nb) == "orgs/3/workspaces/5/notebooks/11/content/"


def test_cursor_round_trip(tmp_path):
    assert s3_indexer._read_cursor(tmp_path) is None
    s3_indexer._write_cursor(tmp_path, 42)
    assert s3_indexer._read_cursor(tmp_path) == 42


def test_lock_for_notebook_is_stable_per_id_and_distinct_across_ids():
    lock_a1 = s3_indexer._lock_for_notebook(1)
    lock_a2 = s3_indexer._lock_for_notebook(1)
    lock_b = s3_indexer._lock_for_notebook(2)
    assert lock_a1 is lock_a2
    assert lock_a1 is not lock_b


# ── path validation ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    "path",
    [
        "../etc/passwd",
        "../../etc/passwd",
        "notes/../../etc/passwd",
        "/etc/passwd",
        "",
    ],
)
def test_is_safe_relative_path_rejects_traversal_and_absolute(path):
    assert s3_indexer.is_safe_relative_path(path) is False


@pytest.mark.parametrize("path", ["readme.md", "notes/hello.md", "a/b/c.md"])
def test_is_safe_relative_path_accepts_notebook_relative_paths(path):
    assert s3_indexer.is_safe_relative_path(path) is True


def test_local_path_raises_for_traversal(tmp_path):
    with pytest.raises(ValueError):
        s3_indexer._local_path(tmp_path, "../../etc/passwd")


def test_local_path_accepts_safe_relative_path(tmp_path):
    result = s3_indexer._local_path(tmp_path, "notes/hello.md")
    assert result == (tmp_path / "notes" / "hello.md").resolve()


# ── rebuild_notebook_index ────────────────────────────────────────────


def test_rebuild_notebook_index_noop_when_s3_not_configured(shared_workspace, monkeypatch):
    workspace, notebook = shared_workspace
    monkeypatch.setattr(s3_indexer, "is_s3_configured", lambda: False)

    result = s3_indexer.rebuild_notebook_index(workspace, notebook)

    assert result.processed == 0
    assert result.deleted == 0


def test_rebuild_notebook_index_materializes_files_and_creates_blocks(shared_workspace, fake_s3):
    workspace, notebook = shared_workspace
    prefix = _prefix(workspace, notebook)
    fake_s3.put(f"{prefix}notes/hello.md", b"# Hello\n", version_id="v1")
    fake_s3.put(f"{prefix}readme.md", b"top level", version_id="v1")

    result = s3_indexer.rebuild_notebook_index(workspace, notebook)

    assert result.processed == 2
    assert result.errors == []

    notebook_path = s3_indexer.notebook_working_copy_path(workspace, notebook)
    assert (notebook_path / "notes" / "hello.md").read_bytes() == b"# Hello\n"
    assert (notebook_path / "readme.md").read_bytes() == b"top level"

    session = get_notebook_session(str(notebook_path))
    try:
        paths = {b.path for b in session.execute(select(Block)).scalars().all()}
    finally:
        session.close()
    assert paths == {"notes/hello.md", "readme.md"}


def test_rebuild_notebook_index_removes_stale_local_blocks(shared_workspace, fake_s3):
    workspace, notebook = shared_workspace
    prefix = _prefix(workspace, notebook)
    fake_s3.put(f"{prefix}keep.md", b"keep me", version_id="v1")
    fake_s3.put(f"{prefix}gone.md", b"will be removed upstream", version_id="v1")

    # First rebuild materializes both files.
    s3_indexer.rebuild_notebook_index(workspace, notebook)
    notebook_path = s3_indexer.notebook_working_copy_path(workspace, notebook)
    assert (notebook_path / "gone.md").exists()

    # Now the object disappears from S3 (deleted by some other client) and we rebuild again.
    fake_s3.delete(f"{prefix}gone.md")
    result = s3_indexer.rebuild_notebook_index(workspace, notebook)

    assert result.deleted == 1
    assert not (notebook_path / "gone.md").exists()

    session = get_notebook_session(str(notebook_path))
    try:
        paths = {b.path for b in session.execute(select(Block)).scalars().all()}
    finally:
        session.close()
    assert paths == {"keep.md"}


def test_rebuild_notebook_index_skips_unsafe_stale_block_path(shared_workspace, fake_s3):
    """A corrupted/malicious Block.path (e.g. containing '..') must not crash the cold-start
    rebuild -- it should be logged and skipped like any other stale-cleanup failure."""
    workspace, notebook = shared_workspace
    prefix = _prefix(workspace, notebook)
    fake_s3.put(f"{prefix}keep.md", b"keep me", version_id="v1")

    # First rebuild establishes the working copy + notebook DB.
    s3_indexer.rebuild_notebook_index(workspace, notebook)
    notebook_path = s3_indexer.notebook_working_copy_path(workspace, notebook)

    # Inject a Block row with an unsafe path directly, simulating corrupted local state --
    # this file no longer exists in S3, so it becomes a stale-cleanup candidate.
    notebook_session = get_notebook_session(str(notebook_path))
    try:
        notebook_session.add(
            Block(
                notebook_id=notebook.id,
                block_id="bad-block",
                path="../../etc/passwd",
                block_type="text",
            )
        )
        notebook_session.commit()
    finally:
        notebook_session.close()

    result = s3_indexer.rebuild_notebook_index(workspace, notebook)

    # The unsafe stale path is skipped (not counted as deleted, doesn't raise).
    assert result.deleted == 0


def test_rebuild_notebook_index_writes_cursor_file(shared_workspace, fake_s3):
    workspace, notebook = shared_workspace
    s3_indexer.rebuild_notebook_index(workspace, notebook)
    notebook_path = s3_indexer.notebook_working_copy_path(workspace, notebook)
    # No sync_journal rows exist for this (unpersisted) notebook id, so the baseline is 0.
    assert s3_indexer._read_cursor(notebook_path) == 0


# ── apply_journal_entry ───────────────────────────────────────────────


def _journal_entry(nb_id, ws_id, path, version, op="created"):
    return SyncJournal(nb_id=nb_id, ws_id=ws_id, path=path, s3_version_id=version, op=op, actor_principal_id=None)


def test_apply_journal_entry_falls_back_to_rebuild_without_working_copy(shared_workspace, fake_s3):
    workspace, notebook = shared_workspace
    prefix = _prefix(workspace, notebook)
    fake_s3.put(f"{prefix}a.md", b"a", version_id="v1")
    entry = _journal_entry(notebook.id, workspace.id, "a.md", "v1")

    s3_indexer.apply_journal_entry(workspace, notebook, entry)

    notebook_path = s3_indexer.notebook_working_copy_path(workspace, notebook)
    assert (notebook_path / "a.md").read_bytes() == b"a"


def test_apply_journal_entry_created_writes_file_and_block(shared_workspace, fake_s3):
    workspace, notebook = shared_workspace
    # Establish a working copy first (cold-start rebuild), then apply an incremental change.
    s3_indexer.rebuild_notebook_index(workspace, notebook)

    prefix = _prefix(workspace, notebook)
    fake_s3.put(f"{prefix}new.md", b"brand new content", version_id="v1")
    entry = _journal_entry(notebook.id, workspace.id, "new.md", "v1")

    s3_indexer.apply_journal_entry(workspace, notebook, entry)

    notebook_path = s3_indexer.notebook_working_copy_path(workspace, notebook)
    assert (notebook_path / "new.md").read_bytes() == b"brand new content"

    session = get_notebook_session(str(notebook_path))
    try:
        block = session.execute(select(Block).where(Block.path == "new.md")).scalar_one_or_none()
    finally:
        session.close()
    assert block is not None


def test_apply_journal_entry_deleted_removes_file_and_block(shared_workspace, fake_s3):
    workspace, notebook = shared_workspace
    prefix = _prefix(workspace, notebook)
    fake_s3.put(f"{prefix}temp.md", b"will be deleted", version_id="v1")
    s3_indexer.rebuild_notebook_index(workspace, notebook)

    notebook_path = s3_indexer.notebook_working_copy_path(workspace, notebook)
    assert (notebook_path / "temp.md").exists()

    fake_s3.delete(f"{prefix}temp.md")
    entry = _journal_entry(notebook.id, workspace.id, "temp.md", "v1", op="deleted")
    s3_indexer.apply_journal_entry(workspace, notebook, entry)

    assert not (notebook_path / "temp.md").exists()
    session = get_notebook_session(str(notebook_path))
    try:
        block = session.execute(select(Block).where(Block.path == "temp.md")).scalar_one_or_none()
    finally:
        session.close()
    assert block is None


# ── concurrency ───────────────────────────────────────────────────────


def test_concurrent_rebuilds_of_same_notebook_are_serialized(shared_workspace, fake_s3, monkeypatch):
    workspace, notebook = shared_workspace
    prefix = _prefix(workspace, notebook)
    fake_s3.put(f"{prefix}a.md", b"a", version_id="v1")
    fake_s3.put(f"{prefix}b.md", b"b", version_id="v1")

    events: list[str] = []
    original = s3_indexer._materialize_object

    def slow_materialize(*args, **kwargs):
        events.append("start")
        time.sleep(0.05)
        result = original(*args, **kwargs)
        events.append("end")
        return result

    monkeypatch.setattr(s3_indexer, "_materialize_object", slow_materialize)

    threads = [threading.Thread(target=s3_indexer.rebuild_notebook_index, args=(workspace, notebook)) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    # Each rebuild processes 2 files; if the two concurrent rebuilds interleaved instead of
    # being serialized by the per-notebook lock, a "start" from thread B could land between
    # thread A's "start" and its matching "end" pair.
    for i in range(0, len(events), 2):
        assert events[i : i + 2] == ["start", "end"], events


# ── S3IndexerService integration (real system DB + push-complete API) ──


def test_service_poll_once_indexes_shared_workspace_from_journal(test_client, auth_headers, create_workspace, fake_s3):
    headers = auth_headers[0]
    workspace = create_workspace()
    nb_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/",
        json={"name": "Shared Notebook"},
        headers=headers,
    )
    assert nb_response.status_code == 200
    notebook = nb_response.json()

    # Mark the workspace as org-owned (shared) directly in the system DB.
    session = get_system_session_sync()
    try:
        ws_row = session.get(Workspace, workspace["id"])
        ws_row.org_id = 12345
        session.add(ws_row)
        session.commit()
    finally:
        session.close()

    ws_prefix = f"orgs/12345/workspaces/{workspace['id']}/notebooks/{notebook['id']}/content/"
    fake_s3.put(f"{ws_prefix}journal-test.md", b"from s3", version_id="v1")

    push_response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/sync/push-complete",
        json={
            "notebook_slug": notebook["slug"],
            "path": "journal-test.md",
            "s3_version_id": "v1",
            "op": "created",
        },
        headers=headers,
    )
    assert push_response.status_code == 200

    service = s3_indexer.S3IndexerService()
    service.poll_once()

    notebook_path = (Path(workspace["path"]) / notebook["path"]).resolve()
    assert (notebook_path / "journal-test.md").read_bytes() == b"from s3"

    nb_session = get_notebook_session(str(notebook_path))
    try:
        block = nb_session.execute(select(Block).where(Block.path == "journal-test.md")).scalar_one_or_none()
    finally:
        nb_session.close()
    assert block is not None


def test_service_poll_once_ignores_personal_workspaces(test_client, workspace_and_notebook, fake_s3):
    workspace, notebook = workspace_and_notebook
    notebook_path = (Path(workspace["path"]) / notebook["path"]).resolve()
    init_notebook_db(str(notebook_path))

    service = s3_indexer.S3IndexerService()
    service.poll_once()

    assert notebook["id"] not in service._cursors
    assert s3_indexer._read_cursor(notebook_path) is None
