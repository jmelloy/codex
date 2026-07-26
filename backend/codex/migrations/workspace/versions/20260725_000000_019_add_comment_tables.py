"""Add comments and comment_mentions tables

Revision ID: 019
Revises: 018
Create Date: 2026-07-25

Adds the Comment and CommentMention tables (issue #529, design doc §4).
Comments are anchored to a block's stable ULID rather than its notebook-local
numeric id, so a thread survives the block being renamed or moved.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "019"
down_revision: str | None = "018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id"), nullable=False, index=True),
        sa.Column("notebook_id", sa.Integer(), sa.ForeignKey("notebooks.id"), nullable=False, index=True),
        sa.Column("block_id", sa.String(), nullable=False, index=True),
        sa.Column("thread_id", sa.Integer(), sa.ForeignKey("comments.id"), nullable=True, index=True),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.String(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "comment_mentions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("comment_id", sa.Integer(), sa.ForeignKey("comments.id"), nullable=False, index=True),
        sa.Column(
            "mentioned_principal_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True
        ),
        sa.Column("handle", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("comment_mentions")
    op.drop_table("comments")
