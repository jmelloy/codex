"""Add markdown_files table for frontmatter indexing

Revision ID: 004_add_markdown_files_table
Revises: 003_add_users_table
Create Date: 2025-12-23

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "004_add_markdown_files_table"
down_revision = "003_add_users_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add markdown_files table for indexing frontmatter metadata."""
    op.create_table(
        "markdown_files",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("relative_path", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("file_hash", sa.String(), nullable=False),
        sa.Column("frontmatter", sa.Text(), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("file_modified", sa.DateTime(), nullable=True),
        sa.Column("indexed_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("relative_path"),
    )
    op.create_index("idx_markdown_files_path", "markdown_files", ["path"], unique=False)
    op.create_index("idx_markdown_files_relative_path", "markdown_files", ["relative_path"], unique=True)
    op.create_index("idx_markdown_files_title", "markdown_files", ["title"], unique=False)
    op.create_index("idx_markdown_files_file_hash", "markdown_files", ["file_hash"], unique=False)


def downgrade() -> None:
    """Remove markdown_files table."""
    op.drop_index("idx_markdown_files_file_hash", table_name="markdown_files")
    op.drop_index("idx_markdown_files_title", table_name="markdown_files")
    op.drop_index("idx_markdown_files_relative_path", table_name="markdown_files")
    op.drop_index("idx_markdown_files_path", table_name="markdown_files")
    op.drop_table("markdown_files")
