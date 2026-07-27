"""S3 sync conflict detection + conflict copies (issue #543, design doc §3.4).

Compare-and-swap semantics over versioned S3: a writer's `push-complete` call
reports the `base_s3_version_id` it last saw for a path. If the journal's
latest entry for that path has since moved on, the two writes raced. The new
write still lands in place (bucket versioning already kept both), but the
losing version -- the one that was current when the race started -- is copied
out to a `name (conflict YYYY-MM-DD).ext` sibling key so both versions stay
directly reachable.

Uses `codex.core.s3_storage.get_s3_client()` / `S3_BUCKET`, the same
connection the rest of sync uses.
"""

import logging
import posixpath
from datetime import date

from botocore.exceptions import ClientError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.core.s3_storage import S3_BUCKET, get_s3_client
from codex.db.models import SyncJournal

logger = logging.getLogger(__name__)


def build_conflict_copy_key(path: str, when: date, disambiguator: int = 1) -> str:
    """Build the conflict-copy key for `path`, e.g. `notes/a.md` -> `notes/a (conflict 2026-07-27).md`.

    `disambiguator` > 1 appends a counter (` (2)`, ` (3)`, ...) for the rare
    case where a path already has a conflict copy recorded for the same day.
    """
    dir_, base = posixpath.split(path)
    stem, ext = posixpath.splitext(base)
    suffix = f" (conflict {when.isoformat()})" if disambiguator == 1 else f" (conflict {when.isoformat()} {disambiguator})"
    new_base = f"{stem}{suffix}{ext}"
    return posixpath.join(dir_, new_base) if dir_ else new_base


async def get_latest_journal_entry(
    session: AsyncSession, *, ws_id: int, nb_id: int, path: str
) -> SyncJournal | None:
    """Return the most recently journaled row for `path`, or None if never seen."""
    result = await session.execute(
        select(SyncJournal)
        .where(SyncJournal.ws_id == ws_id, SyncJournal.nb_id == nb_id, SyncJournal.path == path)
        .order_by(SyncJournal.id.desc())
        .limit(1)
    )
    return result.scalars().first()


async def unique_conflict_copy_path(
    session: AsyncSession, *, ws_id: int, nb_id: int, path: str, when: date
) -> str:
    """Find a `path`'s conflict-copy key that isn't already used for `when`, bumping the disambiguator."""
    disambiguator = 1
    while True:
        candidate = build_conflict_copy_key(path, when, disambiguator)
        existing = await get_latest_journal_entry(session, ws_id=ws_id, nb_id=nb_id, path=candidate)
        if existing is None:
            return candidate
        disambiguator += 1


def copy_object_version(source_key: str, source_version_id: str, dest_key: str, bucket: str | None = None) -> str:
    """Copy a specific S3 object version to `dest_key`. Returns the new object's version id.

    Raises RuntimeError if S3 isn't configured, ValueError if the copy is rejected by S3
    (e.g. the source version no longer exists).
    """
    bucket = bucket or S3_BUCKET
    if not bucket:
        raise RuntimeError("CODEX_S3_BUCKET is not configured")

    client = get_s3_client()
    try:
        resp = client.copy_object(
            Bucket=bucket,
            CopySource={"Bucket": bucket, "Key": source_key, "VersionId": source_version_id},
            Key=dest_key,
        )
    except ClientError as e:
        logger.error("Failed to copy conflict version %s of %s to %s: %s", source_version_id, source_key, dest_key, e)
        raise ValueError(f"Failed to create conflict copy: {e}") from e

    return resp.get("VersionId", "null")
