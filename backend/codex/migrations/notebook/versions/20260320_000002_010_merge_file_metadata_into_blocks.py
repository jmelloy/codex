"""Merge file_metadata into blocks

Revision ID: 010
Revises: 009
Create Date: 2026-03-20

Adds all FileMetadata columns to blocks, backfills data from file_metadata,
updates search_index to reference blocks, then drops file_metadata.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()

    # Add new columns to blocks (from FileMetadata)
    for col_name, col_type, default in [
        ("filename", sa.String(), None),
        ("hash", sa.String(), None),
        ("file_type", sa.String(), None),
        ("sidecar_path", sa.String(), None),
        ("file_created_at", sa.DateTime(), None),
        ("file_modified_at", sa.DateTime(), None),
        ("s3_bucket", sa.String(), None),
        ("s3_key", sa.String(), None),
        ("s3_version_id", sa.String(), None),
        ("git_tracked", sa.Boolean(), True),
        ("last_commit_hash", sa.String(), None),
    ]:
        try:
            if default is not None:
                op.add_column("blocks", sa.Column(col_name, col_type, nullable=True, server_default=str(default)))
            else:
                op.add_column("blocks", sa.Column(col_name, col_type, nullable=True))
        except Exception:
            pass  # Column may already exist

    # Backfill blocks from file_metadata where blocks have a file_id
    has_file_metadata = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name='file_metadata'")
    ).first()

    if has_file_metadata:
        # Backfill blocks that have a file_id linking to file_metadata
        conn.execute(
            sa.text("""
                UPDATE blocks SET
                    filename = COALESCE(blocks.filename, (SELECT fm.filename FROM file_metadata fm WHERE fm.id = blocks.file_id)),
                    hash = COALESCE(blocks.hash, (SELECT fm.hash FROM file_metadata fm WHERE fm.id = blocks.file_id)),
                    file_type = COALESCE(blocks.file_type, (SELECT fm.file_type FROM file_metadata fm WHERE fm.id = blocks.file_id)),
                    sidecar_path = COALESCE(blocks.sidecar_path, (SELECT fm.sidecar_path FROM file_metadata fm WHERE fm.id = blocks.file_id)),
                    file_created_at = COALESCE(blocks.file_created_at, (SELECT fm.file_created_at FROM file_metadata fm WHERE fm.id = blocks.file_id)),
                    file_modified_at = COALESCE(blocks.file_modified_at, (SELECT fm.file_modified_at FROM file_metadata fm WHERE fm.id = blocks.file_id)),
                    s3_bucket = COALESCE(blocks.s3_bucket, (SELECT fm.s3_bucket FROM file_metadata fm WHERE fm.id = blocks.file_id)),
                    s3_key = COALESCE(blocks.s3_key, (SELECT fm.s3_key FROM file_metadata fm WHERE fm.id = blocks.file_id)),
                    s3_version_id = COALESCE(blocks.s3_version_id, (SELECT fm.s3_version_id FROM file_metadata fm WHERE fm.id = blocks.file_id)),
                    git_tracked = COALESCE(blocks.git_tracked, (SELECT fm.git_tracked FROM file_metadata fm WHERE fm.id = blocks.file_id)),
                    last_commit_hash = COALESCE(blocks.last_commit_hash, (SELECT fm.last_commit_hash FROM file_metadata fm WHERE fm.id = blocks.file_id))
                WHERE blocks.file_id IS NOT NULL
            """)
        )

        # Also backfill by path for blocks without file_id
        conn.execute(
            sa.text("""
                UPDATE blocks SET
                    filename = COALESCE(blocks.filename, (SELECT fm.filename FROM file_metadata fm WHERE fm.notebook_id = blocks.notebook_id AND fm.path = blocks.path)),
                    hash = COALESCE(blocks.hash, (SELECT fm.hash FROM file_metadata fm WHERE fm.notebook_id = blocks.notebook_id AND fm.path = blocks.path)),
                    file_type = COALESCE(blocks.file_type, (SELECT fm.file_type FROM file_metadata fm WHERE fm.notebook_id = blocks.notebook_id AND fm.path = blocks.path)),
                    sidecar_path = COALESCE(blocks.sidecar_path, (SELECT fm.sidecar_path FROM file_metadata fm WHERE fm.notebook_id = blocks.notebook_id AND fm.path = blocks.path)),
                    file_created_at = COALESCE(blocks.file_created_at, (SELECT fm.file_created_at FROM file_metadata fm WHERE fm.notebook_id = blocks.notebook_id AND fm.path = blocks.path)),
                    file_modified_at = COALESCE(blocks.file_modified_at, (SELECT fm.file_modified_at FROM file_metadata fm WHERE fm.notebook_id = blocks.notebook_id AND fm.path = blocks.path)),
                    s3_bucket = COALESCE(blocks.s3_bucket, (SELECT fm.s3_bucket FROM file_metadata fm WHERE fm.notebook_id = blocks.notebook_id AND fm.path = blocks.path)),
                    s3_key = COALESCE(blocks.s3_key, (SELECT fm.s3_key FROM file_metadata fm WHERE fm.notebook_id = blocks.notebook_id AND fm.path = blocks.path)),
                    s3_version_id = COALESCE(blocks.s3_version_id, (SELECT fm.s3_version_id FROM file_metadata fm WHERE fm.notebook_id = blocks.notebook_id AND fm.path = blocks.path)),
                    git_tracked = COALESCE(blocks.git_tracked, (SELECT fm.git_tracked FROM file_metadata fm WHERE fm.notebook_id = blocks.notebook_id AND fm.path = blocks.path)),
                    last_commit_hash = COALESCE(blocks.last_commit_hash, (SELECT fm.last_commit_hash FROM file_metadata fm WHERE fm.notebook_id = blocks.notebook_id AND fm.path = blocks.path))
                WHERE blocks.file_id IS NULL AND blocks.filename IS NULL
            """)
        )

    # Compute filename from path for any blocks that still don't have one
    conn.execute(
        sa.text("""
            UPDATE blocks SET filename = CASE
                WHEN INSTR(path, '/') > 0 THEN SUBSTR(path, LENGTH(path) - LENGTH(REPLACE(path, '/', '')) + 1)
                ELSE path
            END
            WHERE filename IS NULL AND path IS NOT NULL AND path != ''
        """)
    )

    # Rebuild search_index to use block_id instead of file_id
    has_search_index = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name='search_index'")
    ).first()

    if has_search_index:
        # Save existing data with block_id mapping
        if has_file_metadata:
            conn.execute(
                sa.text("""
                    CREATE TABLE search_index_new (
                        id INTEGER PRIMARY KEY,
                        block_id INTEGER REFERENCES blocks(id),
                        content TEXT NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                """)
            )
            conn.execute(
                sa.text("""
                    INSERT INTO search_index_new (id, block_id, content, updated_at)
                    SELECT si.id, b.id, si.content, si.updated_at
                    FROM search_index si
                    LEFT JOIN blocks b ON b.file_id = si.file_id
                """)
            )
        else:
            # No file_metadata to join against - check if search_index already has block_id
            columns = [row[1] for row in conn.execute(sa.text("PRAGMA table_info(search_index)")).fetchall()]
            conn.execute(
                sa.text("""
                    CREATE TABLE search_index_new (
                        id INTEGER PRIMARY KEY,
                        block_id INTEGER REFERENCES blocks(id),
                        content TEXT NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                """)
            )
            if "block_id" in columns:
                conn.execute(
                    sa.text("""
                        INSERT INTO search_index_new (id, block_id, content, updated_at)
                        SELECT id, block_id, content, updated_at FROM search_index
                    """)
                )

        op.drop_table("search_index")
        op.rename_table("search_index_new", "search_index")
        op.create_index("ix_search_index_block_id", "search_index", ["block_id"])

    # Drop file_id from blocks and drop file_metadata table using batch mode
    with op.batch_alter_table("blocks", recreate="always") as batch_op:
        try:
            batch_op.drop_column("file_id")
        except Exception:
            pass

    # Create indexes for new columns
    try:
        op.create_index("ix_blocks_filename", "blocks", ["filename"])
    except Exception:
        pass
    try:
        op.create_index("ix_blocks_file_type", "blocks", ["file_type"])
    except Exception:
        pass

    # Drop file_metadata table
    if has_file_metadata:
        op.drop_table("file_metadata")


def downgrade() -> None:
    # Recreate file_metadata table
    op.create_table(
        "file_metadata",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("notebook_id", sa.Integer(), nullable=False),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("hash", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("file_type", sa.String(), nullable=True),
        sa.Column("properties", sa.String(), nullable=True),
        sa.Column("sidecar_path", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("file_created_at", sa.DateTime(), nullable=True),
        sa.Column("file_modified_at", sa.DateTime(), nullable=True),
        sa.Column("s3_bucket", sa.String(), nullable=True),
        sa.Column("s3_key", sa.String(), nullable=True),
        sa.Column("s3_version_id", sa.String(), nullable=True),
        sa.Column("git_tracked", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("last_commit_hash", sa.String(), nullable=True),
        sa.UniqueConstraint("notebook_id", "path", name="uq_file_metadata_notebook_path"),
    )
    op.create_index("ix_file_metadata_path", "file_metadata", ["path"])
    op.create_index("ix_file_metadata_filename", "file_metadata", ["filename"])
    op.create_index("ix_file_metadata_file_type", "file_metadata", ["file_type"])
