"""Convert personal_access_tokens.scopes from a free-form string to a JSON list

Revision ID: 018
Revises: 017
Create Date: 2026-07-24

Replaces the old free-form comma-delimited scopes string with a JSON list of
formal PermissionScope values (issue #527). Existing comma-separated values
are split, trimmed, and re-encoded as a JSON array; unknown/blank tokens are
dropped since the new scope system rejects anything outside ALLOWED_SCOPES.
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "018"
down_revision: str | None = "017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ALLOWED_SCOPES = {"workspace:read", "workspace:write", "comments:write", "sync:credentials"}


def upgrade() -> None:
    conn = op.get_bind()

    # Re-encode existing comma-delimited scope strings as JSON arrays before
    # the column is retyped, so no data is lost in the conversion.
    rows = conn.execute(sa.text("SELECT id, scopes FROM personal_access_tokens WHERE scopes IS NOT NULL")).fetchall()
    for row_id, scopes in rows:
        if scopes is None:
            continue
        stripped = scopes.strip()
        if stripped.startswith("["):
            # Already JSON-encoded (e.g. re-running against a partially migrated db).
            continue
        parsed = [s.strip() for s in stripped.split(",") if s.strip() in ALLOWED_SCOPES]
        conn.execute(
            sa.text("UPDATE personal_access_tokens SET scopes = :scopes WHERE id = :id"),
            {"scopes": json.dumps(parsed) if parsed else None, "id": row_id},
        )

    with op.batch_alter_table("personal_access_tokens") as batch_op:
        batch_op.alter_column(
            "scopes",
            existing_type=sa.String(),
            type_=sa.JSON(),
            existing_nullable=True,
        )


def downgrade() -> None:
    conn = op.get_bind()

    with op.batch_alter_table("personal_access_tokens") as batch_op:
        batch_op.alter_column(
            "scopes",
            existing_type=sa.JSON(),
            type_=sa.String(),
            existing_nullable=True,
        )

    rows = conn.execute(sa.text("SELECT id, scopes FROM personal_access_tokens WHERE scopes IS NOT NULL")).fetchall()
    for row_id, scopes in rows:
        if scopes is None:
            continue
        try:
            values = json.loads(scopes)
        except (TypeError, ValueError):
            continue
        conn.execute(
            sa.text("UPDATE personal_access_tokens SET scopes = :scopes WHERE id = :id"),
            {"scopes": ",".join(values) if values else None, "id": row_id},
        )
