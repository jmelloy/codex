"""Initial notebook database schema

Revision ID: 001
Revises:
Create Date: 2025-01-23

This migration creates the initial schema for per-notebook databases:
- file_metadata: Metadata for files in a notebook
- tags: Tags for organizing content
- file_tags: Link table for file tags
- search_index: Full-text search index for file content
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create file_metadata table
    op.create_table(
        "file_metadata",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("notebook_id", sa.Integer(), nullable=False),
        sa.Column("path", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("filename", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("content_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("hash", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("properties", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("sidecar_path", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("file_created_at", sa.DateTime(), nullable=True),
        sa.Column("file_modified_at", sa.DateTime(), nullable=True),
        sa.Column("git_tracked", sa.Boolean(), nullable=False),
        sa.Column("last_commit_hash", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_file_metadata_path"), "file_metadata", ["path"], unique=False)
    op.create_index(op.f("ix_file_metadata_filename"), "file_metadata", ["filename"], unique=False)

    # Create tags table
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("notebook_id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("color", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tags_name"), "tags", ["name"], unique=False)

    # Create file_tags link table
    op.create_table(
        "file_tags",
        sa.Column("file_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["file_metadata.id"]),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"]),
        sa.PrimaryKeyConstraint("file_id", "tag_id"),
    )

    # Create search_index table
    op.create_table(
        "search_index",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("file_id", sa.Integer(), nullable=False),
        sa.Column("content", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["file_metadata.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_search_index_file_id"), "search_index", ["file_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_search_index_file_id"), table_name="search_index")
    op.drop_table("search_index")
    op.drop_table("file_tags")
    op.drop_index(op.f("ix_tags_name"), table_name="tags")
    op.drop_table("tags")
    op.drop_index(op.f("ix_file_metadata_filename"), table_name="file_metadata")
    op.drop_index(op.f("ix_file_metadata_path"), table_name="file_metadata")
    op.drop_table("file_metadata")
