"""S3 storage backend for binary files.

Binary files are uploaded to S3 with versioning enabled. A lightweight
pointer file is kept on the local filesystem (and committed to git)
so that the notebook's git history records every version of the binary.

Environment variables:
    CODEX_S3_BUCKET       – required, the S3 bucket name
    CODEX_S3_PREFIX       – optional key prefix (default "codex/")
    CODEX_S3_REGION       – AWS region (default "us-east-1")
    CODEX_S3_ENDPOINT_URL – custom endpoint for S3-compatible stores (MinIO, R2, etc.)
    AWS_ACCESS_KEY_ID     – standard AWS credential
    AWS_SECRET_ACCESS_KEY – standard AWS credential
"""

import json
import logging
import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
S3_BUCKET: str | None = os.getenv("CODEX_S3_BUCKET")
S3_PREFIX: str = os.getenv("CODEX_S3_PREFIX", "codex/")
S3_REGION: str = os.getenv("CODEX_S3_REGION", "us-east-1")
S3_ENDPOINT_URL: str | None = os.getenv("CODEX_S3_ENDPOINT_URL")

# Presigned URL expiration (seconds)
PRESIGNED_URL_EXPIRY: int = int(os.getenv("CODEX_S3_PRESIGNED_EXPIRY", "3600"))

# Pointer file extension
POINTER_EXT = ".s3ref"

# ---------------------------------------------------------------------------
# Pointer file format
# ---------------------------------------------------------------------------
POINTER_VERSION = 1
POINTER_HEADER = "codex-s3-pointer"


def _build_pointer(bucket: str, key: str, version_id: str, size: int, sha256: str, content_type: str) -> str:
    """Build the content of an S3 pointer file."""
    data = {
        "header": POINTER_HEADER,
        "version": POINTER_VERSION,
        "s3": {
            "bucket": bucket,
            "key": key,
            "version_id": version_id,
        },
        "file": {
            "size": size,
            "sha256": sha256,
            "content_type": content_type,
        },
    }
    return json.dumps(data, indent=2) + "\n"


def parse_pointer(content: str) -> dict | None:
    """Parse a pointer file and return the S3 metadata, or None if invalid."""
    try:
        data = json.loads(content)
        if data.get("header") == POINTER_HEADER:
            return data
    except (json.JSONDecodeError, TypeError):
        pass
    return None


def is_pointer_file(filepath: str) -> bool:
    """Check if a filepath is an S3 pointer file."""
    return filepath.endswith(POINTER_EXT)


# ---------------------------------------------------------------------------
# S3 client (lazy singleton)
# ---------------------------------------------------------------------------
_s3_client = None


def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        kwargs = {"region_name": S3_REGION}
        if S3_ENDPOINT_URL:
            kwargs["endpoint_url"] = S3_ENDPOINT_URL
        _s3_client = boto3.client("s3", **kwargs)
    return _s3_client


def is_s3_configured() -> bool:
    """Return True if S3 storage is configured."""
    return bool(S3_BUCKET)


# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------


def ensure_versioning(bucket: str | None = None) -> bool:
    """Enable versioning on the S3 bucket. Returns True on success."""
    bucket = bucket or S3_BUCKET
    if not bucket:
        return False
    try:
        client = _get_s3_client()
        client.put_bucket_versioning(
            Bucket=bucket,
            VersioningConfiguration={"Status": "Enabled"},
        )
        logger.info("S3 versioning enabled on bucket %s", bucket)
        return True
    except ClientError as e:
        logger.error("Failed to enable S3 versioning on %s: %s", bucket, e)
        return False


def get_versioning_status(bucket: str | None = None) -> str | None:
    """Return the versioning status of the bucket ('Enabled', 'Suspended', or None)."""
    bucket = bucket or S3_BUCKET
    if not bucket:
        return None
    try:
        client = _get_s3_client()
        resp = client.get_bucket_versioning(Bucket=bucket)
        return resp.get("Status")
    except ClientError as e:
        logger.error("Failed to get versioning status for %s: %s", bucket, e)
        return None


# ---------------------------------------------------------------------------
# Upload / Download
# ---------------------------------------------------------------------------


def build_s3_key(workspace_slug: str, notebook_slug: str, relative_path: str) -> str:
    """Build a deterministic S3 key for a file."""
    return f"{S3_PREFIX}{workspace_slug}/{notebook_slug}/{relative_path}"


def upload_binary(
    content: bytes,
    s3_key: str,
    content_type: str = "application/octet-stream",
    bucket: str | None = None,
) -> dict:
    """Upload binary content to S3.

    Returns dict with ``bucket``, ``key``, ``version_id``, ``etag``.
    """
    bucket = bucket or S3_BUCKET
    if not bucket:
        raise RuntimeError("CODEX_S3_BUCKET is not configured")

    client = _get_s3_client()
    resp = client.put_object(
        Bucket=bucket,
        Key=s3_key,
        Body=content,
        ContentType=content_type,
    )

    version_id = resp.get("VersionId", "null")
    etag = resp.get("ETag", "").strip('"')

    logger.info("Uploaded %s to s3://%s/%s (version=%s)", len(content), bucket, s3_key, version_id)

    return {
        "bucket": bucket,
        "key": s3_key,
        "version_id": version_id,
        "etag": etag,
    }


def download_binary(s3_key: str, version_id: str | None = None, bucket: str | None = None) -> bytes:
    """Download binary content from S3."""
    bucket = bucket or S3_BUCKET
    if not bucket:
        raise RuntimeError("CODEX_S3_BUCKET is not configured")

    client = _get_s3_client()
    kwargs: dict = {"Bucket": bucket, "Key": s3_key}
    if version_id and version_id != "null":
        kwargs["VersionId"] = version_id

    resp = client.get_object(**kwargs)
    return resp["Body"].read()


def generate_presigned_url(s3_key: str, version_id: str | None = None, bucket: str | None = None) -> str:
    """Generate a presigned download URL for an S3 object."""
    bucket = bucket or S3_BUCKET
    if not bucket:
        raise RuntimeError("CODEX_S3_BUCKET is not configured")

    client = _get_s3_client()
    params: dict = {"Bucket": bucket, "Key": s3_key}
    if version_id and version_id != "null":
        params["VersionId"] = version_id

    return client.generate_presigned_url("get_object", Params=params, ExpiresIn=PRESIGNED_URL_EXPIRY)


def list_versions(s3_key: str, bucket: str | None = None) -> list[dict]:
    """List all versions of an S3 object."""
    bucket = bucket or S3_BUCKET
    if not bucket:
        return []

    client = _get_s3_client()
    try:
        resp = client.list_object_versions(Bucket=bucket, Prefix=s3_key)
        versions = []
        for v in resp.get("Versions", []):
            if v["Key"] == s3_key:
                versions.append(
                    {
                        "version_id": v["VersionId"],
                        "last_modified": v["LastModified"].isoformat(),
                        "size": v["Size"],
                        "is_latest": v["IsLatest"],
                        "etag": v.get("ETag", "").strip('"'),
                    }
                )
        return versions
    except ClientError as e:
        logger.error("Failed to list versions for %s: %s", s3_key, e)
        return []


# ---------------------------------------------------------------------------
# Pointer file helpers
# ---------------------------------------------------------------------------


def write_pointer_file(
    filepath: str,
    bucket: str,
    s3_key: str,
    version_id: str,
    size: int,
    sha256: str,
    content_type: str,
) -> str:
    """Write a pointer file next to the original binary.

    Returns the path to the pointer file.
    """
    pointer_path = filepath + POINTER_EXT
    pointer_content = _build_pointer(bucket, s3_key, version_id, size, sha256, content_type)
    with open(pointer_path, "w") as f:
        f.write(pointer_content)
    return pointer_path


def read_pointer_file(pointer_path: str) -> dict | None:
    """Read and parse a pointer file from disk."""
    try:
        with open(pointer_path) as f:
            return parse_pointer(f.read())
    except (OSError, IOError):
        return None
