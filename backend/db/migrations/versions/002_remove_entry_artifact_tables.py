"""Remove entry, artifact, and integration tables

Revision ID: 002_remove_entry_artifact_tables
Revises: 001_initial_schema
Create Date: 2025-12-21

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "002_remove_entry_artifact_tables"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove entry, artifact, entry_lineage, entry_tags, and integration_variables tables."""
    # Drop indexes first
    op.drop_index("idx_integration_variables_type_name", table_name="integration_variables")
    op.drop_index("idx_artifacts_hash", table_name="artifacts")
    op.drop_index("idx_artifacts_entry", table_name="artifacts")
    op.drop_index("idx_entries_type", table_name="entries")
    op.drop_index("idx_entries_created", table_name="entries")
    op.drop_index("idx_entries_parent", table_name="entries")
    op.drop_index("idx_entries_page", table_name="entries")
    
    # Drop tables (in order to respect foreign key constraints)
    op.drop_table("integration_variables")
    op.drop_table("entry_tags")
    op.drop_table("entry_lineage")
    op.drop_table("artifacts")
    op.drop_table("entries")


def downgrade() -> None:
    """Recreate entry, artifact, entry_lineage, entry_tags, and integration_variables tables."""
    # Recreate entries table
    op.create_table(
        "entries",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("page_id", sa.String(), nullable=False),
        sa.Column("entry_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("parent_id", sa.String(), nullable=True),
        sa.Column("inputs", sa.Text(), nullable=False),
        sa.Column("outputs", sa.Text(), nullable=True),
        sa.Column("execution", sa.Text(), nullable=True),
        sa.Column("metrics", sa.Text(), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["page_id"],
            ["pages.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["entries.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_entries_page", "entries", ["page_id"], unique=False)
    op.create_index("idx_entries_parent", "entries", ["parent_id"], unique=False)
    op.create_index("idx_entries_created", "entries", ["created_at"], unique=False)
    op.create_index("idx_entries_type", "entries", ["entry_type"], unique=False)
    
    # Recreate artifacts table
    op.create_table(
        "artifacts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("entry_id", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("hash", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("thumbnail_path", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=True),
        sa.Column("archive_strategy", sa.String(), nullable=True),
        sa.Column("original_size_bytes", sa.Integer(), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["entry_id"],
            ["entries.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hash"),
    )
    op.create_index("idx_artifacts_entry", "artifacts", ["entry_id"], unique=False)
    op.create_index("idx_artifacts_hash", "artifacts", ["hash"], unique=False)
    
    # Recreate entry_lineage table
    op.create_table(
        "entry_lineage",
        sa.Column("parent_id", sa.String(), nullable=False),
        sa.Column("child_id", sa.String(), nullable=False),
        sa.Column("relationship_type", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["entries.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["child_id"],
            ["entries.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("parent_id", "child_id"),
    )
    
    # Recreate entry_tags table
    op.create_table(
        "entry_tags",
        sa.Column("entry_id", sa.String(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["entry_id"],
            ["entries.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.id"],
        ),
        sa.PrimaryKeyConstraint("entry_id", "tag_id"),
    )
    
    # Recreate integration_variables table
    op.create_table(
        "integration_variables",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("integration_type", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_secret", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_integration_variables_type_name",
        "integration_variables",
        ["integration_type", "name"],
        unique=True,
    )
