"""S3 sync credential vendor: scoped STS credentials + presigned URL fallback.

Implements design doc §3.3 ("The backend as token authority") and issue #540.
Clients never hold long-lived AWS keys; this module mints short-lived, scoped
credentials on demand, using the bucket layout from §3.2:

    s3://{bucket}/orgs/{org_id}/workspaces/{ws_id}/...      # org workspaces
    s3://{bucket}/users/{owner_id}/workspaces/{ws_id}/...   # personal workspaces

Two vending paths:
    - `vend_sts_credentials()` — STS AssumeRole with an inline session policy
      scoped to the workspace's prefix. Preferred; requires CODEX_SYNC_ROLE_ARN.
    - `generate_presigned_batch()` — per-object presigned URLs for get/put/
      delete/list, for S3-compatible stores without STS support.

Environment variables:
    CODEX_SYNC_ROLE_ARN        – IAM role to assume for scoped sessions (required for STS)
    CODEX_SYNC_EXTERNAL_ID     – optional STS ExternalId, for cross-account trust hardening
    CODEX_SYNC_CREDENTIAL_TTL  – credential/presign lifetime in seconds (default 3600)
    CODEX_SYNC_STS_ENDPOINT_URL – custom STS endpoint (defaults to CODEX_S3_ENDPOINT_URL,
                                   since MinIO serves STS from the same endpoint as S3)

Reuses CODEX_S3_BUCKET / CODEX_S3_REGION / CODEX_S3_ENDPOINT_URL from `s3_storage`
for the underlying bucket connection.
"""

import json
import logging
import os
import posixpath
from typing import Literal

import boto3
from botocore.exceptions import ClientError

from codex.core.s3_storage import S3_BUCKET, S3_ENDPOINT_URL, S3_REGION, get_s3_client
from codex.db.models import Workspace

logger = logging.getLogger(__name__)

SYNC_ROLE_ARN: str | None = os.getenv("CODEX_SYNC_ROLE_ARN")
SYNC_EXTERNAL_ID: str | None = os.getenv("CODEX_SYNC_EXTERNAL_ID")
SYNC_CREDENTIAL_TTL: int = int(os.getenv("CODEX_SYNC_CREDENTIAL_TTL", "3600"))
SYNC_STS_ENDPOINT_URL: str | None = os.getenv("CODEX_SYNC_STS_ENDPOINT_URL", S3_ENDPOINT_URL)

PresignOperation = Literal["get", "put", "delete", "list"]

# (boto3 ClientMethod, HTTP method) for each supported presign operation.
_PRESIGN_OPS: dict[str, tuple[str, str]] = {
    "get": ("get_object", "GET"),
    "put": ("put_object", "PUT"),
    "delete": ("delete_object", "DELETE"),
    "list": ("list_objects_v2", "GET"),
}
WRITE_OPERATIONS = {"put", "delete"}

_sts_client = None


def _get_sts_client():
    global _sts_client
    if _sts_client is None:
        kwargs = {"region_name": S3_REGION}
        if SYNC_STS_ENDPOINT_URL:
            kwargs["endpoint_url"] = SYNC_STS_ENDPOINT_URL
        _sts_client = boto3.client("sts", **kwargs)
    return _sts_client


def is_sts_configured() -> bool:
    """Return True if STS AssumeRole vending is available (role ARN + bucket set)."""
    return bool(SYNC_ROLE_ARN and S3_BUCKET)


def build_workspace_prefix(workspace: Workspace) -> str:
    """Return the S3 key prefix a workspace's sync traffic is scoped to (design doc §3.2)."""
    if workspace.org_id is not None:
        return f"orgs/{workspace.org_id}/workspaces/{workspace.id}/"
    return f"users/{workspace.owner_id}/workspaces/{workspace.id}/"


def build_session_policy(bucket: str, prefix: str, write: bool) -> dict:
    """Build the inline IAM session policy scoping access to `prefix` within `bucket`.

    Object-level actions (Get/Put/Delete) are scoped via the Resource ARN pattern.
    ListBucket is a bucket-level action, so it's scoped separately with an
    `s3:prefix` condition — without this, a caller could enumerate the entire
    bucket even though they can't read/write outside their prefix.
    """
    bucket_arn = f"arn:aws:s3:::{bucket}"
    object_actions = ["s3:GetObject", "s3:GetObjectVersion"]
    if write:
        object_actions += ["s3:PutObject", "s3:DeleteObject", "s3:DeleteObjectVersion"]

    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ObjectAccess",
                "Effect": "Allow",
                "Action": object_actions,
                "Resource": f"{bucket_arn}/{prefix}*",
            },
            {
                "Sid": "ListPrefix",
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": bucket_arn,
                "Condition": {"StringLike": {"s3:prefix": [f"{prefix}*"]}},
            },
        ],
    }


def vend_sts_credentials(workspace: Workspace, write: bool) -> dict:
    """AssumeRole into a session scoped to `workspace`'s prefix. Raises RuntimeError if unconfigured."""
    if not is_sts_configured():
        raise RuntimeError("CODEX_SYNC_ROLE_ARN / CODEX_S3_BUCKET is not configured")

    prefix = build_workspace_prefix(workspace)
    policy = build_session_policy(S3_BUCKET, prefix, write)

    kwargs: dict = {
        "RoleArn": SYNC_ROLE_ARN,
        "RoleSessionName": f"codex-ws{workspace.id}"[:64],
        "Policy": json.dumps(policy),
        "DurationSeconds": SYNC_CREDENTIAL_TTL,
    }
    if SYNC_EXTERNAL_ID:
        kwargs["ExternalId"] = SYNC_EXTERNAL_ID

    client = _get_sts_client()
    try:
        resp = client.assume_role(**kwargs)
    except ClientError as e:
        logger.error("STS AssumeRole failed for workspace %s: %s", workspace.id, e)
        raise RuntimeError(f"STS AssumeRole failed: {e}") from e

    creds = resp["Credentials"]
    return {
        "access_key_id": creds["AccessKeyId"],
        "secret_access_key": creds["SecretAccessKey"],
        "session_token": creds["SessionToken"],
        "expiration": creds["Expiration"],
        "bucket": S3_BUCKET,
        "prefix": prefix,
        "region": S3_REGION,
        "endpoint_url": S3_ENDPOINT_URL,
    }


def _resolve_key(prefix: str, relative_key: str) -> str:
    """Join `relative_key` onto `prefix`, rejecting anything that would escape it.

    S3 keys are opaque strings, not filesystem paths, but clients may still send
    "../" segments trying to reach outside their workspace prefix -- reject those
    before they ever reach `generate_presigned_url`.
    """
    relative_key = relative_key.strip("/")
    if not relative_key:
        return prefix

    normalized = posixpath.normpath(relative_key)
    if normalized == "." or normalized.startswith("..") or normalized.startswith("/"):
        raise ValueError(f"Key escapes workspace prefix: {relative_key!r}")
    return f"{prefix}{normalized}"


def generate_presigned_batch(
    workspace: Workspace, items: list[tuple[str, str]], expiry: int | None = None
) -> tuple[str, str, list[dict]]:
    """Generate presigned URLs for a batch of (key, operation) pairs.

    `operation` is one of "get"/"put"/"delete"/"list". Keys are relative to the
    workspace's prefix; an empty key with operation "list" lists the whole
    workspace. Returns (bucket, prefix, [{key, operation, method, url}]).
    Raises RuntimeError if S3 isn't configured, ValueError for a bad key/op.
    """
    if not S3_BUCKET:
        raise RuntimeError("CODEX_S3_BUCKET is not configured")

    prefix = build_workspace_prefix(workspace)
    expiry = expiry or SYNC_CREDENTIAL_TTL
    client = get_s3_client()

    results = []
    for relative_key, operation in items:
        if operation not in _PRESIGN_OPS:
            raise ValueError(f"Unsupported operation: {operation!r}")
        client_method, http_method = _PRESIGN_OPS[operation]
        full_key = _resolve_key(prefix, relative_key)

        params: dict = {"Bucket": S3_BUCKET}
        if operation == "list":
            params["Prefix"] = full_key
        else:
            params["Key"] = full_key

        url = client.generate_presigned_url(client_method, Params=params, ExpiresIn=expiry)
        results.append(
            {
                "key": relative_key,
                "operation": operation,
                "method": http_method,
                "url": url,
            }
        )

    return S3_BUCKET, prefix, results
