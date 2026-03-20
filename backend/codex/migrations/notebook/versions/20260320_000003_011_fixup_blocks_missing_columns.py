"""Fixup: add missing columns to blocks table

Revision ID: 011
Revises: 010
Create Date: 2026-03-20

Migration 010's batch_alter_table(recreate="always") could drop columns
that were added earlier in the same migration due to SQLite inspector
caching. This fixup re-adds any missing columns and cleans up leftover
file_metadata/file_id if they still exist.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "011"
down_revision: str | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()

    # Check which columns blocks currently has
    existing_cols = {
        row[1]
        for row in conn.execute(sa.text("PRAGMA table_info(blocks)")).fetchall()
    }

    # All columns that should exist on blocks after migration 010
    required_columns = [
        ("filename", "TEXT"),
        ("hash", "TEXT"),
        ("file_type", "TEXT"),
        ("sidecar_path", "TEXT"),
        ("file_created_at", "TIMESTAMP"),
        ("file_modified_at", "TIMESTAMP"),
        ("s3_bucket", "TEXT"),
        ("s3_key", "TEXT"),
        ("s3_version_id", "TEXT"),
        ("git_tracked", "BOOLEAN DEFAULT 1"),
        ("last_commit_hash", "TEXT"),
    ]

    # Add any missing columns via raw DDL (avoids Alembic op caching issues)
    for col_name, col_def in required_columns:
        if col_name not in existing_cols:
            conn.execute(
                sa.text(f"ALTER TABLE blocks ADD COLUMN {col_name} {col_def}")
            )

    # Backfill from file_metadata if it still exists
    has_file_metadata = conn.execute(
        sa.text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='file_metadata'"
        )
    ).first()

    has_file_id = "file_id" in existing_cols or "file_id" in {
        row[1]
        for row in conn.execute(sa.text("PRAGMA table_info(blocks)")).fetchall()
    }

    if has_file_metadata and has_file_id:
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

    # Drop file_id column and file_metadata table if they still exist
    if has_file_id:
        # Rebuild search_index if it still references file_id
        si_cols = {
            row[1]
            for row in conn.execute(
                sa.text("PRAGMA table_info(search_index)")
            ).fetchall()
        }
        if "file_id" in si_cols:
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
            if has_file_metadata:
                conn.execute(
                    sa.text("""
                        INSERT INTO search_index_new (id, block_id, content, updated_at)
                        SELECT si.id, b.id, si.content, si.updated_at
                        FROM search_index si
                        LEFT JOIN blocks b ON b.file_id = si.file_id
                    """)
                )
            elif "block_id" in si_cols:
                conn.execute(
                    sa.text("""
                        INSERT INTO search_index_new (id, block_id, content, updated_at)
                        SELECT id, block_id, content, updated_at FROM search_index
                    """)
                )
            conn.execute(sa.text("DROP TABLE search_index"))
            conn.execute(
                sa.text("ALTER TABLE search_index_new RENAME TO search_index")
            )
            try:
                op.create_index(
                    "ix_search_index_block_id", "search_index", ["block_id"]
                )
            except Exception:
                pass

        # Use raw SQL to recreate blocks without file_id
        # (avoids batch_alter_table caching bug)
        cols_info = conn.execute(sa.text("PRAGMA table_info(blocks)")).fetchall()
        keep_cols = [row[1] for row in cols_info if row[1] != "file_id"]

        if "file_id" in [row[1] for row in cols_info]:
            cols_csv = ", ".join(keep_cols)

            # Build column definitions for the new table
            col_defs = []
            for row in cols_info:
                cid, name, ctype, notnull, dflt, pk = row
                if name == "file_id":
                    continue
                parts = [name, ctype or "TEXT"]
                if pk:
                    parts.append("PRIMARY KEY AUTOINCREMENT")
                elif notnull:
                    parts.append("NOT NULL")
                if dflt is not None:
                    parts.append(f"DEFAULT {dflt}")
                col_defs.append(" ".join(parts))

            conn.execute(
                sa.text(
                    f"CREATE TABLE blocks_new ({', '.join(col_defs)})"
                )
            )
            conn.execute(
                sa.text(
                    f"INSERT INTO blocks_new ({cols_csv}) SELECT {cols_csv} FROM blocks"
                )
            )
            conn.execute(sa.text("DROP TABLE blocks"))
            conn.execute(
                sa.text("ALTER TABLE blocks_new RENAME TO blocks")
            )

            # Recreate indexes
            for idx_name, idx_cols in [
                ("ix_blocks_block_id", ["block_id"]),
                ("ix_blocks_parent_block_id", ["parent_block_id"]),
                ("ix_blocks_path", ["path"]),
                ("ix_blocks_notebook_parent", ["notebook_id", "parent_block_id"]),
                ("ix_blocks_filename", ["filename"]),
                ("ix_blocks_file_type", ["file_type"]),
            ]:
                try:
                    op.create_index(idx_name, "blocks", idx_cols)
                except Exception:
                    pass

            # Recreate unique constraints via indexes
            try:
                conn.execute(
                    sa.text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS uq_blocks_notebook_block_id ON blocks (notebook_id, block_id)"
                    )
                )
            except Exception:
                pass
            try:
                conn.execute(
                    sa.text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS uq_blocks_notebook_path ON blocks (notebook_id, path)"
                    )
                )
            except Exception:
                pass

    # Drop file_metadata table if it still exists
    if has_file_metadata:
        conn.execute(sa.text("DROP TABLE IF EXISTS file_metadata"))

    # Drop file_tags if it still exists (should have been dropped by 009)
    conn.execute(sa.text("DROP TABLE IF EXISTS file_tags"))


def downgrade() -> None:
    # This is a fixup migration - downgrade is a no-op
    # (migration 010's downgrade handles the full reversal)
    pass
