"""Add organizations and org_memberships tables

Revision ID: 024
Revises: 023
Create Date: 2026-07-26

Adds the Organization and OrgMembership models (issue #537, design doc §2.2).
`OrgMembership.role` is one of "owner" | "admin" | "member" | "guest"; the
(org_id, principal_id) pair is unique so a principal holds exactly one role
per organization. Role-gated management and last-owner protection are
enforced at the API layer (codex.core.org_permissions), not in the schema.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "024"
down_revision: str | None = "023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "org_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("principal_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("role", sa.String(), nullable=False, server_default="member"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("org_id", "principal_id", name="uq_org_memberships_org_principal"),
    )


def downgrade() -> None:
    op.drop_table("org_memberships")
    op.drop_table("organizations")
