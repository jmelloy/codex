"""Add blocks table for infinite block recursion

Revision ID: 007
Revises: 006
Create Date: 2026-03-18

Adds a blocks table to support Notion-like infinite nested block structure.
Each block is backed by a file on disk; pages (blocks with children) are
folders containing a .codex-page.json metadata file.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "blocks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("notebook_id", sa.Integer(), nullable=False),
        sa.Column("block_id", sa.String(), nullable=False),
        sa.Column("parent_block_id", sa.String(), nullable=True),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("block_type", sa.String(), nullable=False),
        sa.Column("content_format", sa.String(), nullable=False, server_default="markdown"),
        sa.Column("order_index", sa.Float(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("file_id", sa.Integer(), sa.ForeignKey("file_metadata.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("notebook_id", "block_id", name="uq_blocks_notebook_block_id"),
        sa.UniqueConstraint("notebook_id", "path", name="uq_blocks_notebook_path"),
    )
    op.create_index("ix_blocks_block_id", "blocks", ["block_id"])
    op.create_index("ix_blocks_parent_block_id", "blocks", ["parent_block_id"])
    op.create_index("ix_blocks_path", "blocks", ["path"])
    op.create_index("ix_blocks_notebook_parent", "blocks", ["notebook_id", "parent_block_id"])


def downgrade() -> None:
    op.drop_index("ix_blocks_notebook_parent")
    op.drop_index("ix_blocks_path")
    op.drop_index("ix_blocks_parent_block_id")
    op.drop_index("ix_blocks_block_id")
    op.drop_table("blocks")
