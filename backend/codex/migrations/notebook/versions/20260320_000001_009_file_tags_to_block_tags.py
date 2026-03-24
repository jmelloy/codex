"""Migrate file_tags to block_tags

Revision ID: 009
Revises: 008
Create Date: 2026-03-20

Moves the tag relationship from files to blocks. Creates a new block_tags
table, migrates existing file_tags by looking up the corresponding block
for each file, then drops the old file_tags table.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create new block_tags link table
    op.create_table(
        "block_tags",
        sa.Column("block_id", sa.Integer(), sa.ForeignKey("blocks.id"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tags.id"), primary_key=True),
    )

    # Migrate existing file_tags → block_tags via blocks.file_id (if table exists)
    conn = op.get_bind()
    has_file_tags = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name='file_tags'")
    ).first()

    if has_file_tags:
        conn.execute(
            sa.text(
                "INSERT OR IGNORE INTO block_tags (block_id, tag_id) "
                "SELECT b.id, ft.tag_id "
                "FROM file_tags ft "
                "JOIN blocks b ON b.file_id = ft.file_id"
            )
        )
        op.drop_table("file_tags")


def downgrade() -> None:
    # Recreate file_tags
    op.create_table(
        "file_tags",
        sa.Column("file_id", sa.Integer(), sa.ForeignKey("file_metadata.id"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tags.id"), primary_key=True),
    )

    # Migrate back: block_tags → file_tags via blocks.file_id
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "INSERT OR IGNORE INTO file_tags (file_id, tag_id) "
            "SELECT b.file_id, bt.tag_id "
            "FROM block_tags bt "
            "JOIN blocks b ON b.id = bt.block_id "
            "WHERE b.file_id IS NOT NULL"
        )
    )

    op.drop_table("block_tags")
