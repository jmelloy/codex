"""Fix workspace slug constraint to be unique per owner

Revision ID: 008
Revises: 007
Create Date: 2026-02-03

This migration fixes the workspace slug constraint to be unique per owner
instead of globally unique. This allows different users to have workspaces
with the same slug, similar to how notebooks work (unique per workspace).
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Change workspace slug constraint to be unique per owner."""
    with op.batch_alter_table("workspaces") as batch_op:
        # Drop the old global unique constraint
        batch_op.drop_constraint("uq_notebooks_workspace_slug", type_="unique")
        # Create new unique constraint on (owner_id, slug)
        batch_op.create_unique_constraint("uq_workspaces_owner_slug", ["owner_id", "slug"])


def downgrade() -> None:
    """Revert to global unique constraint on slug."""
    with op.batch_alter_table("workspaces") as batch_op:
        # Drop the per-owner unique constraint
        batch_op.drop_constraint("uq_workspaces_owner_slug", type_="unique")
        # Restore the old global unique constraint
        batch_op.create_unique_constraint("uq_workspaces_slug", ["slug"])
