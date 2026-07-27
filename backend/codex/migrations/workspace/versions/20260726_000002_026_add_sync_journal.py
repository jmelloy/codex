"""Add sync_journal table

Revision ID: 026
Revises: 025
Create Date: 2026-07-26

Adds the append-only SyncJournal table backing the S3 sync change feed
(issue #541, design doc §3.2/§3.4). Rows are populated from a client's
`POST .../sync/push-complete` call and/or an S3 bucket event notification
where configured; `id` is a strictly monotonic, never-reused autoincrement
(`sqlite_autoincrement`) used as the `GET .../sync/changes?since=cursor`
pull cursor. The unique constraint on (ws_id, nb_id, path, s3_version_id)
deduplicates the same S3 object version being reported twice; ws_id/nb_id
are part of the key because `path` is only notebook-relative, so distinct
notebooks can legitimately share a path (e.g. two "readme.md" files).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "026"
down_revision: str | None = "025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sync_journal",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ws_id", sa.Integer(), sa.ForeignKey("workspaces.id"), nullable=False, index=True),
        sa.Column("nb_id", sa.Integer(), sa.ForeignKey("notebooks.id"), nullable=False, index=True),
        sa.Column("path", sa.String(), nullable=False, index=True),
        sa.Column("s3_version_id", sa.String(), nullable=False),
        sa.Column("actor_principal_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("op", sa.String(), nullable=False, index=True),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("ws_id", "nb_id", "path", "s3_version_id", name="uq_sync_journal_path_version"),
        sqlite_autoincrement=True,
    )


def downgrade() -> None:
    op.drop_table("sync_journal")
