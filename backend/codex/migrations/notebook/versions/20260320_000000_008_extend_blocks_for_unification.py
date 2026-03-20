"""Extend blocks table for file/folder unification

Revision ID: 008
Revises: 007
Create Date: 2026-03-20

Adds denormalized fields to blocks table and backfills Block rows
for every FileMetadata row that doesn't already have one.
"""

import json
import os
from collections.abc import Sequence
from pathlib import Path

from ulid import ULID

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add new columns to blocks table
    op.add_column("blocks", sa.Column("content_type", sa.String(), nullable=True))
    op.add_column("blocks", sa.Column("size", sa.Integer(), nullable=True))
    op.add_column("blocks", sa.Column("description", sa.String(), nullable=True))
    op.add_column("blocks", sa.Column("properties", sa.String(), nullable=True))

    # Backfill: create Block rows for FileMetadata rows that don't have one
    conn = op.get_bind()

    # Get all file_metadata rows
    files = conn.execute(
        sa.text("SELECT id, notebook_id, path, filename, content_type, size, title, description, properties FROM file_metadata")
    ).fetchall()

    # Get existing block file_ids and paths
    existing_block_file_ids = set()
    existing_block_paths = set()
    try:
        rows = conn.execute(sa.text("SELECT file_id, path, notebook_id FROM blocks")).fetchall()
        for row in rows:
            if row[0] is not None:
                existing_block_file_ids.add(row[0])
            existing_block_paths.add((row[2], row[1]))  # (notebook_id, path)
    except Exception:
        pass

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()

    for f in files:
        file_id, notebook_id, path, filename, content_type, size, title, description, properties = f

        # Skip if block already exists for this file
        if file_id in existing_block_file_ids:
            # Update denormalized fields on existing block
            conn.execute(
                sa.text(
                    "UPDATE blocks SET content_type = :ct, size = :sz, description = :desc, properties = :props "
                    "WHERE file_id = :fid"
                ),
                {"ct": content_type, "sz": size, "desc": description, "props": properties, "fid": file_id},
            )
            continue

        # Skip if block already exists at this path
        if (notebook_id, path) in existing_block_paths:
            continue

        # Skip hidden/metadata files
        if filename in (".metadata", ".codex-page.json"):
            continue

        # Determine block type from content_type
        if content_type and content_type.startswith("image/"):
            block_type = "image"
        elif content_type and content_type.startswith("text/"):
            block_type = "text"
        else:
            block_type = "file"

        # Determine parent: check if file is in a directory that has a page block
        parent_block_id = None
        parts = path.split("/")
        if len(parts) > 1:
            parent_path = "/".join(parts[:-1])
            parent_row = conn.execute(
                sa.text(
                    "SELECT block_id FROM blocks WHERE notebook_id = :nid AND path = :p AND block_type = 'page'"
                ),
                {"nid": notebook_id, "p": parent_path},
            ).first()
            if parent_row:
                parent_block_id = parent_row[0]

        block_id = str(ULID())
        content_format = "binary" if (content_type and not content_type.startswith("text/")) else "markdown"

        conn.execute(
            sa.text(
                "INSERT INTO blocks (notebook_id, block_id, parent_block_id, path, block_type, "
                "content_format, order_index, title, file_id, content_type, size, description, "
                "properties, created_at, updated_at) "
                "VALUES (:nid, :bid, :pbid, :path, :btype, :cfmt, :order, :title, :fid, "
                ":ct, :sz, :desc, :props, :created, :updated)"
            ),
            {
                "nid": notebook_id,
                "bid": block_id,
                "pbid": parent_block_id,
                "path": path,
                "btype": block_type,
                "cfmt": content_format,
                "order": 0.0,
                "title": title,
                "fid": file_id,
                "ct": content_type,
                "sz": size,
                "desc": description,
                "props": properties,
                "created": now,
                "updated": now,
            },
        )


def downgrade() -> None:
    # Remove blocks that were auto-created (have file_id set and aren't pages)
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM blocks WHERE file_id IS NOT NULL AND block_type != 'page'")
    )

    op.drop_column("blocks", "properties")
    op.drop_column("blocks", "description")
    op.drop_column("blocks", "size")
    op.drop_column("blocks", "content_type")
