"""Organization CRUD and role-gated membership management (issue #537).

Organizations group principals (humans and bots) via `OrgMembership` role
grants - see docs/design/multi-user-multi-org.md §2.2. Role gating and
last-owner protection are enforced through `codex.core.org_permissions`.
"""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete, select

from codex.api.auth import get_current_active_user
from codex.api.routes.utils import slugify
from codex.api.schemas import MessageResponse
from codex.core.org_permissions import (
    VALID_ORG_ROLES,
    OrgRoleRank,
    can_assign_role,
    can_manage_target,
    count_owners,
    get_membership,
    require_org_membership,
)
from codex.db.database import get_system_session
from codex.db.models import Organization, OrgMembership, OrgRole, User


class OrganizationCreate(BaseModel):
    """Request body for creating an organization."""

    name: str = Field(..., min_length=1, max_length=100)


class OrganizationUpdate(BaseModel):
    """Request body for renaming an organization."""

    name: str = Field(..., min_length=1, max_length=100)


class OrganizationResponse(BaseModel):
    """An organization, with the caller's own role when known."""

    id: int
    name: str
    slug: str
    my_role: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class MembershipInvite(BaseModel):
    """Request body for inviting a principal (human or bot) to an organization."""

    username_or_email: str
    role: str = OrgRole.MEMBER.value


class MembershipUpdate(BaseModel):
    """Request body for changing a member's role."""

    role: str


class MembershipResponse(BaseModel):
    """A single organization membership entry."""

    principal_id: int
    username: str
    email: str
    role: str
    is_bot: bool = False
    display_name: str | None = None
    created_at: str | None = None


router = APIRouter()
members_router = APIRouter()


def _validate_role(value: str) -> str:
    role = value.lower()
    if role not in VALID_ORG_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid organization role: {value!r}. Must be one of {sorted(VALID_ORG_ROLES)}",
        )
    return role


async def _find_principal_by_username_or_email(session: AsyncSession, username_or_email: str) -> User | None:
    result = await session.execute(
        select(User).where((User.username == username_or_email) | (User.email == username_or_email))
    )
    return result.scalar_one_or_none()


async def _slug_exists(session: AsyncSession, slug: str) -> bool:
    result = await session.execute(select(Organization).where(Organization.slug == slug))
    return result.scalar_one_or_none() is not None


async def get_org_by_slug(
    org_slug: str,
    current_user: User,
    session: AsyncSession,
    required_rank: OrgRoleRank = OrgRoleRank.GUEST,
) -> tuple[Organization, OrgMembership]:
    """Get an organization by slug, asserting the caller has at least `required_rank`.

    Raises 404 if no such org exists or the caller isn't a member (so org
    existence isn't leaked to outsiders), 403 if a member but below `required_rank`.
    """
    result = await session.execute(select(Organization).where(Organization.slug == org_slug))
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    membership = await require_org_membership(session, org.id, current_user.id, required_rank)
    return org, membership


def _serialize_org(org: Organization, my_role: str | None) -> OrganizationResponse:
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        my_role=my_role,
        created_at=org.created_at.isoformat() if org.created_at else None,
        updated_at=org.updated_at.isoformat() if org.updated_at else None,
    )


def _serialize_membership(membership: OrgMembership, principal: User) -> MembershipResponse:
    return MembershipResponse(
        principal_id=principal.id,
        username=principal.username,
        email=principal.email,
        role=membership.role,
        is_bot=principal.is_bot,
        display_name=principal.display_name,
        created_at=membership.created_at.isoformat() if membership.created_at else None,
    )


@router.post("/", response_model=OrganizationResponse, status_code=201)
async def create_organization(
    body: OrganizationCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Create an organization. The creator becomes its sole owner."""
    base_slug = slugify(body.name, default="org")
    final_slug = base_slug
    while await _slug_exists(session, final_slug):
        final_slug = f"{base_slug}-{uuid4().hex[:8]}"

    org = Organization(name=body.name, slug=final_slug)
    session.add(org)
    await session.flush()

    session.add(OrgMembership(org_id=org.id, principal_id=current_user.id, role=OrgRole.OWNER.value))

    await session.commit()
    await session.refresh(org)
    return _serialize_org(org, OrgRole.OWNER.value)


@router.get("/", response_model=list[OrganizationResponse])
async def list_organizations(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """List organizations the current user (or bot) belongs to."""
    result = await session.execute(
        select(Organization, OrgMembership.role)
        .join(OrgMembership, OrgMembership.org_id == Organization.id)
        .where(OrgMembership.principal_id == current_user.id)
    )
    return [_serialize_org(org, role) for org, role in result.all()]


@router.get("/{org_slug}", response_model=OrganizationResponse)
async def get_organization(
    org_slug: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Get an organization by slug. Requires membership at any role."""
    org, membership = await get_org_by_slug(org_slug, current_user, session)
    return _serialize_org(org, membership.role)


@router.patch("/{org_slug}", response_model=OrganizationResponse)
async def update_organization(
    org_slug: str,
    body: OrganizationUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Rename an organization. Requires admin or owner."""
    org, membership = await get_org_by_slug(org_slug, current_user, session, required_rank=OrgRoleRank.ADMIN)

    org.name = body.name
    org.updated_at = datetime.now(UTC)
    session.add(org)
    await session.commit()
    await session.refresh(org)
    return _serialize_org(org, membership.role)


@router.delete("/{org_slug}", response_model=MessageResponse)
async def delete_organization(
    org_slug: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Delete an organization and all its memberships. Requires owner."""
    org, _ = await get_org_by_slug(org_slug, current_user, session, required_rank=OrgRoleRank.OWNER)

    await session.execute(delete(OrgMembership).where(OrgMembership.org_id == org.id))
    await session.delete(org)
    await session.commit()

    return {"message": "Organization deleted"}


@members_router.get("/", response_model=list[MembershipResponse])
async def list_members(
    org_slug: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """List an organization's members. Requires at least member role (guests can't see the roster)."""
    org, _ = await get_org_by_slug(org_slug, current_user, session, required_rank=OrgRoleRank.MEMBER)

    result = await session.execute(
        select(OrgMembership, User).join(User, User.id == OrgMembership.principal_id).where(
            OrgMembership.org_id == org.id
        )
    )
    return [_serialize_membership(membership, principal) for membership, principal in result.all()]


@members_router.post("/", response_model=MembershipResponse, status_code=201)
async def invite_member(
    org_slug: str,
    body: MembershipInvite,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Invite a principal (human or bot) by username/email, granting a role.

    Requires admin or owner. Assigning the admin or owner role itself requires
    owner (`can_assign_role`).
    """
    org, actor_membership = await get_org_by_slug(org_slug, current_user, session, required_rank=OrgRoleRank.ADMIN)

    role = _validate_role(body.role)
    actor_rank = OrgRoleRank.from_str(actor_membership.role)
    if not can_assign_role(actor_rank, OrgRoleRank.from_str(role)):
        raise HTTPException(status_code=403, detail="Only an owner can assign the admin or owner role")

    principal = await _find_principal_by_username_or_email(session, body.username_or_email)
    if principal is None:
        raise HTTPException(status_code=404, detail="No user found matching that username or email")

    if await get_membership(session, org.id, principal.id) is not None:
        raise HTTPException(status_code=400, detail="This principal is already a member of the organization")

    membership = OrgMembership(org_id=org.id, principal_id=principal.id, role=role)
    session.add(membership)
    await session.commit()
    await session.refresh(membership)

    return _serialize_membership(membership, principal)


@members_router.patch("/{principal_id}", response_model=MembershipResponse)
async def update_member_role(
    org_slug: str,
    principal_id: int,
    body: MembershipUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Change a member's role.

    Requires admin or owner, and the actor must outrank the member's *current*
    role (an admin cannot touch another admin or an owner). Assigning the
    admin or owner role requires owner. The last owner cannot be demoted.
    """
    org, actor_membership = await get_org_by_slug(org_slug, current_user, session, required_rank=OrgRoleRank.ADMIN)

    target = await get_membership(session, org.id, principal_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Member not found")

    new_role = _validate_role(body.role)
    actor_rank = OrgRoleRank.from_str(actor_membership.role)
    target_rank = OrgRoleRank.from_str(target.role)

    if not can_manage_target(actor_rank, target_rank):
        raise HTTPException(status_code=403, detail="Insufficient organization role to manage this member")
    if not can_assign_role(actor_rank, OrgRoleRank.from_str(new_role)):
        raise HTTPException(status_code=403, detail="Only an owner can assign the admin or owner role")

    if target.role == OrgRole.OWNER.value and new_role != OrgRole.OWNER.value:
        if await count_owners(session, org.id) <= 1:
            raise HTTPException(status_code=400, detail="Cannot demote the last owner")

    target.role = new_role
    target.updated_at = datetime.now(UTC)
    session.add(target)
    await session.commit()
    await session.refresh(target)

    principal = await session.get(User, principal_id)
    if principal is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return _serialize_membership(target, principal)


@members_router.delete("/{principal_id}", response_model=MessageResponse)
async def remove_member(
    org_slug: str,
    principal_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Remove a member from the organization.

    Requires admin or owner, and the actor must outrank the member's current
    role. The last owner cannot be removed.
    """
    org, actor_membership = await get_org_by_slug(org_slug, current_user, session, required_rank=OrgRoleRank.ADMIN)

    target = await get_membership(session, org.id, principal_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Member not found")

    actor_rank = OrgRoleRank.from_str(actor_membership.role)
    target_rank = OrgRoleRank.from_str(target.role)
    if not can_manage_target(actor_rank, target_rank):
        raise HTTPException(status_code=403, detail="Insufficient organization role to manage this member")

    if target.role == OrgRole.OWNER.value and await count_owners(session, org.id) <= 1:
        raise HTTPException(status_code=400, detail="Cannot remove the last owner")

    await session.delete(target)
    await session.commit()

    return {"message": "Member removed"}
