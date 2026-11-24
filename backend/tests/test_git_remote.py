"""Tests for remote git support (issue #627)."""

import pytest
from git import Repo

from codex.core.git_manager import GitManager
from codex.core.git_remote import (
    RemoteGitError,
    git_auth_env,
    redact_url,
    validate_ref,
    validate_remote_url,
)


@pytest.mark.parametrize(
    "url",
    ["https://github.com/o/r.git", "ssh://git@gitlab.com/o/r.git", "git@github.com:o/r.git", "git://host/r", "https://host:8443/r"],
)
def test_valid_urls(url):
    assert validate_remote_url(url) == url


@pytest.mark.parametrize(
    "url", ["", "/tmp/repo", "file:///tmp/repo", "ext::sh -c id", "--upload-pack=x", "https://", "../x", "http://example.com/r.git", "ssh://-oProxyCommand=x/r", "ssh://u:pw@host/r", "git@-host:r"]
)
def test_invalid_urls(url):
    with pytest.raises(RemoteGitError):
        validate_remote_url(url)


def test_validate_strips_credentials():
    assert validate_remote_url("https://user:tok@github.com/o/r.git") == "https://github.com/o/r.git"
    assert validate_remote_url("https://tok@host:8443/o/r") == "https://host:8443/o/r"
    assert validate_remote_url("ssh://git@host/o/r") == "ssh://git@host/o/r"


def test_clone_uses_sanitized_url(monkeypatch, tmp_path):
    from codex.core import git_remote

    seen = {}
    monkeypatch.setattr(
        git_remote.Repo, "clone_from", lambda url, dest, **kw: seen.setdefault("url", url)
    )
    git_remote.clone_repository("https://u:tok@example.com/o/r.git", str(tmp_path / "d"))
    assert seen["url"] == "https://example.com/o/r.git"


def test_set_remote_persists_sanitized_url(tmp_path):
    gm = GitManager(str(tmp_path))
    gm.set_remote("origin", "https://u:tok@example.com/o/r.git")
    assert "tok" not in (tmp_path / ".git" / "config").read_text()
    assert gm.repo.remote("origin").url == "https://example.com/o/r.git"


def test_invalid_ref():
    with pytest.raises(RemoteGitError):
        validate_ref("--force")
    with pytest.raises(RemoteGitError):
        validate_ref("a..b")


def test_redact_url():
    assert redact_url("https://user:tok@github.com/o/r.git") == "https://github.com/o/r.git"
    assert redact_url("git@github.com:o/r.git") == "git@github.com:o/r.git"


def test_auth_env_token_and_key_cleanup():
    import os

    with git_auth_env(token="sekret", ssh_private_key="KEY") as (env, secrets):
        assert "sekret" not in env["GIT_CONFIG_VALUE_0"]  # base64 encoded
        assert "sekret" in secrets
        key_path = env["GIT_SSH_COMMAND"].split("-i ")[1].split(" ")[0]
        assert os.path.exists(key_path)
        assert oct(os.stat(key_path).st_mode & 0o777) == "0o600"
    assert not os.path.exists(key_path)


@pytest.fixture
def bare_remote(tmp_path):
    path = tmp_path / "remote.git"
    Repo.init(path, bare=True)
    return path


def _seed(path, name, content):
    gm = GitManager(str(path))
    f = path / name
    f.write_text(content)
    gm.commit(f"add {name}", [str(f)])
    return gm


def test_set_list_remove_remote(tmp_path):
    gm = GitManager(str(tmp_path))
    gm.set_remote("origin", "https://user:pw@example.com/o/r.git")
    assert gm.list_remotes() == [{"name": "origin", "url": "https://example.com/o/r.git"}]
    gm.set_remote("origin", "https://example.com/other.git")
    assert gm.list_remotes()[0]["url"] == "https://example.com/other.git"
    with pytest.raises(RemoteGitError):
        gm.set_remote("origin", "/etc/passwd")
    assert gm.remove_remote("origin") is True
    assert gm.remove_remote("origin") is False


def test_push_fetch_pull_roundtrip(tmp_path, bare_remote):
    a = tmp_path / "a"
    a.mkdir()
    gm_a = _seed(a, "one.md", "one")
    # Local path remotes are blocked by set_remote validation, so configure directly.
    gm_a.repo.create_remote("origin", str(bare_remote))
    gm_a.remote_operation("push")

    b = tmp_path / "b"
    Repo.clone_from(str(bare_remote), b)
    gm_b = GitManager(str(b))
    branch = gm_a.repo.active_branch.name
    gm_b.remote_operation("fetch")
    assert (b / "one.md").read_text() == "one"

    _seed(a, "two.md", "two")
    gm_a.remote_operation("push")
    gm_b.remote_operation("pull", ref=branch)
    assert (b / "two.md").read_text() == "two"


def test_operation_without_remote(tmp_path):
    gm = GitManager(str(tmp_path))
    with pytest.raises(RemoteGitError):
        gm.remote_operation("fetch")


def test_failed_operation_is_scrubbed(tmp_path):
    gm = GitManager(str(tmp_path))
    gm.repo.create_remote("origin", str(tmp_path / "does-not-exist"))
    with pytest.raises(RemoteGitError) as exc:
        gm.remote_operation("fetch", token="sekret")
    assert "sekret" not in str(exc.value)


def test_remote_api(test_client, auth_headers, create_workspace, monkeypatch):
    headers = auth_headers[0]
    ws = create_workspace()
    base = f"/api/v1/workspaces/{ws['slug']}/notebooks"
    nb = test_client.post(f"{base}/", json={"name": "NB"}, headers=headers).json()

    r = test_client.put(
        f"{base}/{nb['slug']}/remotes/", json={"url": "https://x:y@example.com/o/r.git"}, headers=headers
    )
    assert r.status_code == 200 and r.json()["url"] == "https://example.com/o/r.git"
    r = test_client.get(f"{base}/{nb['slug']}/remotes/", headers=headers)
    assert r.json() == [{"name": "origin", "url": "https://example.com/o/r.git"}]
    r = test_client.put(f"{base}/{nb['slug']}/remotes/", json={"url": "file:///tmp/x"}, headers=headers)
    assert r.status_code == 400
    r = test_client.post(f"{base}/{nb['slug']}/remotes/fetch", json={"remote": "nope"}, headers=headers)
    assert r.status_code == 400
    r = test_client.delete(f"{base}/{nb['slug']}/remotes/origin", headers=headers)
    assert r.status_code == 200


def test_clone_api(test_client, auth_headers, create_workspace, monkeypatch, tmp_path):
    headers = auth_headers[0]
    ws = create_workspace()
    src = tmp_path / "src"
    src.mkdir()
    _seed(src, "hello.md", "hi")

    from codex.api.routes import git_remote

    def fake_clone(url, dest, branch=None, **auth):
        return Repo.clone_from(str(src), dest)

    monkeypatch.setattr(git_remote, "clone_repository", fake_clone)
    monkeypatch.setattr(git_remote, "NotebookWatcher", lambda *a, **k: type("W", (), {"start": lambda s: None})())
    base = f"/api/v1/workspaces/{ws['slug']}/notebooks"
    r = test_client.post(f"{base}/clone", json={"url": "https://example.com/o/my-repo.git"}, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["slug"] == "my-repo"
    r = test_client.post(f"{base}/clone", json={"url": "/local/path"}, headers=headers)
    assert r.status_code == 400
