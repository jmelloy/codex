"""Backfill content_format: markdown -> legacy

Revision ID: 012
Revises: 011
Create Date: 2026-08-15

`content_format` is already a free-form string column (used for "markdown",
"json", "binary"), so no schema change is needed here. This migration only
backfills existing rows: blocks previously tagged "markdown" become "legacy"
so the new MDX rendering pipeline and component registry only apply to
blocks explicitly created (or migrated) as "mdx". Going forward, new blocks
default to "mdx" (see Block.content_format in codex/db/models/notebook.py
and the create_block()/create_page() defaults in codex/core/blocks.py).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "012"
down_revision: str | None = "011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE blocks SET content_format = 'legacy' WHERE content_format = 'markdown'"))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE blocks SET content_format = 'markdown' WHERE content_format = 'legacy'"))
