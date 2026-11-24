"""Remote git support: URL validation, authentication and clone/fetch/pull/push.

Credentials are never persisted or embedded in remote URLs. They are passed
per-operation: HTTPS tokens via an ``http.extraheader`` config entry (env
based, so it never appears in argv), SSH keys via a temporary key file and
``GIT_SSH_COMMAND``.
"""

import base64
import os
import re
import shlex
import stat
import tempfile
from contextlib import contextmanager
from urllib.parse import urlsplit, urlunsplit

from git import GitCommandError, Repo

ALLOWED_SCHEMES = {"https", "ssh", "git"}
_SCP_RE = re.compile(r"^[A-Za-z0-9._-]+@[A-Za-z0-9.-]+:[^\s]+$")
_REMOTE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")


class RemoteGitError(Exception):
    """Raised for invalid remote input or failed remote operations."""


def validate_remote_url(url: str) -> str:
    """Validate a remote URL and return the sanitized URL to use.

    Only https, ssh, git and scp-style (user@host:path) URLs are accepted.
    Local paths, ``file:``/``ext::``/``http`` transports, option-like values and
    hosts starting with ``-`` are rejected. Embedded credentials are stripped
    from https/git URLs (pass a token via the auth options instead) so they are
    never persisted to ``.git/config``; ssh URLs keep only a bare username and
    reject embedded passwords.
    """
    url = (url or "").strip()
    if not url or url.startswith("-") or any(c.isspace() or ord(c) < 32 for c in url):
        raise RemoteGitError("Invalid remote URL")
    if _SCP_RE.match(url):
        if url.split("@", 1)[1].startswith("-"):
            raise RemoteGitError("Invalid remote host")
        return url
    try:
        parts = urlsplit(url)
        host = parts.hostname
        port = parts.port
    except ValueError:
        raise RemoteGitError("Invalid remote URL") from None
    if parts.scheme not in ALLOWED_SCHEMES or not host:
        raise RemoteGitError("Remote URL must be https, ssh, git or user@host:path")
    if host.startswith("-") or (parts.username or "").startswith("-"):
        raise RemoteGitError("Invalid remote host")
    if parts.password is not None:
        if parts.scheme == "ssh":
            raise RemoteGitError("Embedded passwords are not allowed in remote URLs")
    netloc = f"[{host}]" if ":" in host else host
    if port:
        netloc += f":{port}"
    if parts.scheme == "ssh" and parts.username:
        netloc = f"{parts.username}@{netloc}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def validate_remote_name(name: str) -> str:
    if not _REMOTE_NAME_RE.match(name or ""):
        raise RemoteGitError("Invalid remote name")
    return name


def validate_ref(ref: str) -> str:
    if not _REF_RE.match(ref or "") or ".." in ref:
        raise RemoteGitError("Invalid ref name")
    return ref


def redact_url(url: str) -> str:
    """Strip any embedded user:password from a URL for display."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return url
    if parts.scheme in ("http", "https") and (parts.username or parts.password):
        host = parts.hostname or ""
        if parts.port:
            host += f":{parts.port}"
        return urlunsplit((parts.scheme, host, parts.path, parts.query, parts.fragment))
    return url


def _scrub(message: str, secrets: list[str]) -> str:
    for s in secrets:
        if s:
            message = message.replace(s, "***")
    return message


@contextmanager
def git_auth_env(token: str | None = None, username: str | None = None, ssh_private_key: str | None = None):
    """Yield (env, secrets) for git subprocesses with the given credentials."""
    env = {
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ASKPASS": "echo",
        "GIT_SSH_COMMAND": "ssh -o BatchMode=yes",
    }
    secrets: list[str] = []
    key_path = None
    try:
        if token:
            basic = base64.b64encode(f"{username or 'x-access-token'}:{token}".encode()).decode()
            env["GIT_CONFIG_COUNT"] = "1"
            env["GIT_CONFIG_KEY_0"] = "http.extraheader"
            env["GIT_CONFIG_VALUE_0"] = f"Authorization: Basic {basic}"
            secrets += [token, basic]
        if ssh_private_key:
            fd, key_path = tempfile.mkstemp(prefix="codex-key-")
            with os.fdopen(fd, "w") as f:
                f.write(ssh_private_key.rstrip("\n") + "\n")
            os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)
            env["GIT_SSH_COMMAND"] = (
                f"ssh -i {shlex.quote(key_path)} -o IdentitiesOnly=yes -o BatchMode=yes "
                "-o StrictHostKeyChecking=accept-new"
            )
            secrets.append(ssh_private_key)
        yield env, secrets
    finally:
        if key_path and os.path.exists(key_path):
            os.remove(key_path)


def clone_repository(url: str, dest: str, branch: str | None = None, **auth) -> Repo:
    """Clone ``url`` into the (empty or non-existent) ``dest`` directory."""
    url = validate_remote_url(url)
    if branch:
        validate_ref(branch)
    with git_auth_env(**auth) as (env, secrets):
        try:
            kwargs = {"branch": branch} if branch else {}
            return Repo.clone_from(url, dest, env=env, allow_unsafe_protocols=False, **kwargs)
        except GitCommandError as e:
            raise RemoteGitError(_scrub(str(e.stderr or e), secrets).strip()) from None


def run_remote(repo: Repo, op: str, remote: str, ref: str | None = None, **auth) -> str:
    """Run fetch/pull/push against ``remote`` with credentials; return git output."""
    validate_remote_name(remote)
    if ref:
        validate_ref(ref)
    with git_auth_env(**auth) as (env, secrets):
        try:
            with repo.git.custom_environment(**env):
                if op == "fetch":
                    return repo.git.fetch(remote, "--prune")
                if op == "pull":
                    return repo.git.pull("--ff-only", remote, *([ref] if ref else []))
                if op == "push":
                    target = ref or repo.active_branch.name
                    return repo.git.push("--set-upstream", remote, target)
            raise RemoteGitError(f"Unknown operation: {op}")
        except GitCommandError as e:
            raise RemoteGitError(_scrub(str(e.stderr or e), secrets).strip()) from None
        except TypeError:
            raise RemoteGitError("Cannot push from a detached HEAD") from None
