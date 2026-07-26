"""Organization role resolution and role-gated membership management.

Mirrors `codex.core.permissions` but for the org/role hierarchy instead of the
workspace/permission-level hierarchy (issue #537, design doc §2.2).

Role hierarchy, lowest to highest: guest < member < admin < owner.

Management rule ("admins manage members, owners manage admins"):
- An owner can manage (invite, remove, change the role of) any membership,
  including other owners.
- An admin can only manage memberships whose *current* role is below admin
  (member/guest) - never another admin or an owner.
- Assigning the admin or owner role to anyone requires the actor to be an
  owner; an admin can only assign member/guest roles.

Last-owner protection: an org must always have at least one owner, so the
last remaining owner can neither be demoted nor removed.
"""

from enum import IntEnum

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.db.models import OrgMembership, OrgRole


class OrgRoleRank(IntEnum):
    """Org roles ordered from least to most access."""

    GUEST = 1
    MEMBER = 2
    ADMIN = 3
    OWNER = 4

    @classmethod
    def from_str(cls, value: str) -> "OrgRoleRank":
        """Parse a stored role string (e.g. "admin") into a rank."""
        try:
            return cls[value.upper()]
        except KeyError:
            raise ValueError(f"Unknown org role: {value!r}") from None


VALID_ORG_ROLES = {role.value for role in OrgRole}


async def get_membership(session: AsyncSession, org_id: int, principal_id: int) -> OrgMembership | None:
    """Fetch a principal's membership row for an org, or None if not a member."""
    result = await session.execute(
        select(OrgMembership).where(
            OrgMembership.org_id == org_id,
            OrgMembership.principal_id == principal_id,
        )
    )
    return result.scalar_one_or_none()


def has_rank(rank: OrgRoleRank | None, required: OrgRoleRank) -> bool:
    """Return True if `rank` meets or exceeds `required` in the hierarchy."""
    if rank is None:
        return False
    return rank >= required


async def require_org_membership(
    session: AsyncSession,
    org_id: int,
    principal_id: int,
    required: OrgRoleRank = OrgRoleRank.GUEST,
) -> OrgMembership:
    """Assert `principal_id` is a member of `org_id` with at least `required` rank.

    Raises a 404 if not a member at all (so org existence isn't leaked to
    outsiders) and a 403 if a member but below `required`.
    """
    membership = await get_membership(session, org_id, principal_id)
    if membership is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    if not has_rank(OrgRoleRank.from_str(membership.role), required):
        raise HTTPException(status_code=403, detail="Insufficient organization role for this operation")
    return membership


def can_manage_target(actor_rank: OrgRoleRank, target_rank: OrgRoleRank) -> bool:
    """Return True if `actor_rank` may manage (edit role of / remove) a membership at `target_rank`."""
    if actor_rank == OrgRoleRank.OWNER:
        return True
    return actor_rank == OrgRoleRank.ADMIN and target_rank < OrgRoleRank.ADMIN


def can_assign_role(actor_rank: OrgRoleRank, new_role: OrgRoleRank) -> bool:
    """Return True if `actor_rank` may assign `new_role` to a membership (new or existing)."""
    if new_role >= OrgRoleRank.ADMIN:
        return actor_rank == OrgRoleRank.OWNER
    return actor_rank >= OrgRoleRank.ADMIN


async def count_owners(session: AsyncSession, org_id: int) -> int:
    """Count how many memberships in `org_id` currently hold the owner role."""
    result = await session.execute(
        select(func.count()).select_from(OrgMembership).where(
            OrgMembership.org_id == org_id,
            OrgMembership.role == OrgRole.OWNER.value,
        )
    )
    return result.scalar_one()
