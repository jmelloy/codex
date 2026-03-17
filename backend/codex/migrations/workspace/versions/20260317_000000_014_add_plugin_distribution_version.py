"""Add distribution_version column to plugins table

Revision ID: 014
Revises: 013
Create Date: 2026-03-17

The plugins table previously stored the S3 distribution version
(e.g. YYYY.MM.release.sha) in the ``version`` column. The ``version``
column now holds the semver string from the plugin manifest, and the
new ``distribution_version`` column holds the S3 distribution version.
Existing rows are migrated by copying the old value to
``distribution_version`` and leaving ``version`` unchanged so that
the column is non-null (existing installs retain what they had).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "014"
down_revision: str | None = "013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("plugins", sa.Column("distribution_version", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("plugins", "distribution_version")
