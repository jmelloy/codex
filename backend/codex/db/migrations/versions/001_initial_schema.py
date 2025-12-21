"""Initial database schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2024-11-28

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the initial database schema."""
    # Create notebooks table
    op.create_table(
        "notebooks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("settings", sa.Text(), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_notebooks_created", "notebooks", ["created_at"], unique=False)

    # Create pages table
    op.create_table(
        "pages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("notebook_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("narrative", sa.Text(), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["notebook_id"],
            ["notebooks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_pages_notebook", "pages", ["notebook_id"], unique=False)
    op.create_index("idx_pages_date", "pages", ["date"], unique=False)

    # Create entries table
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

    # Create artifacts table
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

    # Create entry_lineage table
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

    # Create tags table
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("color", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Create notebook_tags table
    op.create_table(
        "notebook_tags",
        sa.Column("notebook_id", sa.String(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["notebook_id"],
            ["notebooks.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.id"],
        ),
        sa.PrimaryKeyConstraint("notebook_id", "tag_id"),
    )

    # Create page_tags table
    op.create_table(
        "page_tags",
        sa.Column("page_id", sa.String(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["page_id"],
            ["pages.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.id"],
        ),
        sa.PrimaryKeyConstraint("page_id", "tag_id"),
    )

    # Create entry_tags table
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

    # Create integration_variables table
    op.create_table(
        "integration_variables",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
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


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table("integration_variables")
    op.drop_table("entry_tags")
    op.drop_table("page_tags")
    op.drop_table("notebook_tags")
    op.drop_table("tags")
    op.drop_table("entry_lineage")
    op.drop_table("artifacts")
    op.drop_table("entries")
    op.drop_table("pages")
    op.drop_table("notebooks")
