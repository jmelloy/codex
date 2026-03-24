"""Add S3 storage fields to file_metadata

Revision ID: 006
Revises: 005
Create Date: 2025-02-25

Adds s3_bucket, s3_key, and s3_version_id columns so that binary files
can be offloaded to S3 with versioning while keeping lightweight pointer
files in git.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("file_metadata", schema=None) as batch_op:
        batch_op.add_column(sa.Column("s3_bucket", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("s3_key", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("s3_version_id", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("file_metadata", schema=None) as batch_op:
        batch_op.drop_column("s3_version_id")
        batch_op.drop_column("s3_key")
        batch_op.drop_column("s3_bucket")
