"""Org-scoped workspace routes: /orgs/{org_slug}/workspaces/... (issue #538).

Mirrors the personal `/workspaces` routes in `codex.api.routes.workspaces`, but
slugs here are unique per-org (`uq_workspaces_org_slug`) rather than per-owner, and
visibility folds in org role (owner/admin/member get implicit access via
`codex.core.permissions.effective_level`), not just ownership or an explicit grant.
Deeper resources (notebooks, blocks, search, ...) stay mounted under the existing
`/workspaces/{workspace_identifier}/...` paths, which already resolve org-role-based
access through `get_workspace_by_slug`.
"""

import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_current_active_user
from codex.api.routes.organizations import get_org_by_slug
from codex.api.routes.utils import slugify
from codex.api.routes.workspaces import (
    WorkspaceCreate,
    get_workspace_by_slug,
    path_exists_in_db,
    slug_exists_in_db,
)
from codex.core.org_permissions import OrgRoleRank
from codex.core.permissions import PermissionLevel, effective_level
from codex.db.database import DATA_DIRECTORY, get_system_session
from codex.db.models import User, Workspace

router = APIRouter()


@router.get("/")
async def list_org_workspaces(
    org_slug: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> list[Workspace]:
    """List workspaces in an org that the caller can access.

    Requires org membership at any role; within that, only workspaces where the
    caller's resolved `effective_level` is non-None are returned (a guest with no
    explicit grant on a given workspace won't see it, even though they can see the
    org itself).
    """
    org, _ = await get_org_by_slug(org_slug, current_user, session)

    result = await session.execute(select(Workspace).where(Workspace.org_id == org.id))
    workspaces = result.scalars().all()

    visible = []
    for workspace in workspaces:
        if await effective_level(current_user, workspace, session) is not None:
            visible.append(workspace)
    return visible


@router.post("/")
async def create_org_workspace(
    org_slug: str,
    body: WorkspaceCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Workspace:
    """Create a workspace under an org. Requires at least member role."""
    org, _ = await get_org_by_slug(org_slug, current_user, session, required_rank=OrgRoleRank.MEMBER)

    name = body.name

    if body.path:
        workspace_path = Path(body.path).resolve()

        if workspace_path.exists():
            if await path_exists_in_db(session, str(workspace_path)):
                raise HTTPException(status_code=400, detail="Path already in use by another workspace")
        else:
            parent = workspace_path.parent
            if not parent.exists():
                raise HTTPException(status_code=400, detail=f"Parent directory does not exist: {parent}")
            if not os.access(parent, os.W_OK):
                raise HTTPException(status_code=400, detail=f"Parent directory is not writable: {parent}")

        base_slug = slugify(workspace_path.name, default="workspace")
        final_slug = base_slug
        while await slug_exists_in_db(session, final_slug, current_user.id, org_id=org.id):
            final_slug = f"{base_slug}-{uuid4().hex[:8]}"

        path = str(workspace_path)
    else:
        base_slug = slugify(name, default="workspace")
        base_path = Path(DATA_DIRECTORY).resolve() / "workspaces" / "orgs" / org.slug
        workspace_path = base_path / base_slug
        final_slug = base_slug

        while (
            workspace_path.exists()
            or await path_exists_in_db(session, str(workspace_path))
            or await slug_exists_in_db(session, final_slug, current_user.id, org_id=org.id)
        ):
            final_slug = f"{base_slug}-{uuid4().hex[:8]}"
            workspace_path = base_path / final_slug

        path = str(workspace_path)

    workspace_dir = Path(path)
    workspace_dir.mkdir(parents=True, exist_ok=True)

    workspace = Workspace(name=name, slug=final_slug, path=path, owner_id=current_user.id, org_id=org.id)
    session.add(workspace)
    await session.commit()
    await session.refresh(workspace)
    return workspace


@router.get("/{workspace_slug}")
async def get_org_workspace(
    org_slug: str,
    workspace_slug: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
) -> Workspace:
    """Get a single org workspace by slug, asserting at least READ access."""
    org, _ = await get_org_by_slug(org_slug, current_user, session)

    return await get_workspace_by_slug(
        workspace_slug, current_user, session, required_level=PermissionLevel.READ, org_id=org.id
    )
