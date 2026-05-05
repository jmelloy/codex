"""Project routes backed by the tag system.

Projects use the existing tag system:
- Membership tag: project:<slug>
- Role tag:       project:<slug>:<role>
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_current_active_user
from codex.api.routes.workspaces import get_workspace_by_slug
from codex.core.blocks import update_block_properties
from codex.db.database import get_notebook_session, get_system_session
from codex.db.models import Block, Notebook, User

logger = logging.getLogger(__name__)

DEFAULT_ROLES = ["character", "scene", "background", "prop", "concept", "reference", "other"]

nested_router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ProjectSummary(BaseModel):
    slug: str
    name: str
    image_count: int


class ImageInfo(BaseModel):
    id: int
    block_id: str
    notebook_id: int
    notebook_slug: str
    workspace_slug: str
    title: str | None = None
    filename: str | None = None
    content_type: str | None = None
    roles: list[str]


class RoleGroup(BaseModel):
    role: str
    images: list[ImageInfo]


class ProjectDetail(BaseModel):
    slug: str
    name: str
    total_images: int
    roles: list[RoleGroup]


class AssignRequest(BaseModel):
    image_ids: list[str]  # block_id strings (ULIDs)
    roles: list[str]


class UnassignRequest(BaseModel):
    image_ids: list[str]  # block_id strings (ULIDs)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slug_to_name(slug: str) -> str:
    return slug.replace("-", " ").replace("_", " ").title()


def _parse_tags(block: Block) -> list[str]:
    if not block.properties:
        return []
    try:
        props = json.loads(block.properties)
        tags = props.get("tags", [])
        return tags if isinstance(tags, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _extract_all_project_slugs(tags: list[str]) -> dict[str, list[str]]:
    """Return {slug: [roles]} for all project:* membership tags."""
    projects: dict[str, list[str]] = {}
    for tag in tags:
        if not tag.startswith("project:"):
            continue
        parts = tag.split(":", 2)
        if len(parts) == 2:
            slug = parts[1]
            if slug not in projects:
                projects[slug] = []
        elif len(parts) == 3:
            slug, role = parts[1], parts[2]
            if slug not in projects:
                projects[slug] = []
            projects[slug].append(role)
    return projects


def _get_roles_for_block(tags: list[str], slug: str) -> list[str]:
    prefix = f"project:{slug}:"
    return [t[len(prefix):] for t in tags if t.startswith(prefix)]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@nested_router.get("/", response_model=list[ProjectSummary])
async def list_projects(
    workspace_identifier: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """List all projects in the workspace (scans for project:<slug> tags)."""
    workspace = await get_workspace_by_slug(workspace_identifier, current_user, session)
    result = await session.execute(select(Notebook).where(Notebook.workspace_id == workspace.id))
    notebooks = result.scalars().all()
    workspace_path = Path(workspace.path).resolve()

    project_counts: dict[str, int] = {}

    for notebook in notebooks:
        nb_path = workspace_path / notebook.path
        if not nb_path.exists():
            continue
        nb_session = get_notebook_session(str(nb_path))
        try:
            stmt = select(Block).where(
                Block.notebook_id == notebook.id,
                Block.properties.contains('"project:'),
            )
            for block in nb_session.execute(stmt).scalars().all():
                tags = _parse_tags(block)
                for slug in _extract_all_project_slugs(tags):
                    project_counts[slug] = project_counts.get(slug, 0) + 1
        finally:
            nb_session.close()

    return sorted(
        [ProjectSummary(slug=s, name=_slug_to_name(s), image_count=c) for s, c in project_counts.items()],
        key=lambda p: p.slug,
    )


@nested_router.get("/{slug}", response_model=ProjectDetail)
async def get_project(
    workspace_identifier: str,
    slug: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Return images for a project grouped by role."""
    workspace = await get_workspace_by_slug(workspace_identifier, current_user, session)
    result = await session.execute(select(Notebook).where(Notebook.workspace_id == workspace.id))
    notebooks = result.scalars().all()
    workspace_path = Path(workspace.path).resolve()

    membership_tag = f'"project:{slug}"'
    role_images: dict[str, list[ImageInfo]] = {}

    for notebook in notebooks:
        nb_path = workspace_path / notebook.path
        if not nb_path.exists():
            continue
        nb_session = get_notebook_session(str(nb_path))
        try:
            stmt = select(Block).where(
                Block.notebook_id == notebook.id,
                Block.properties.contains(membership_tag),
            )
            for block in nb_session.execute(stmt).scalars().all():
                tags = _parse_tags(block)
                if f"project:{slug}" not in tags:
                    continue
                roles = _get_roles_for_block(tags, slug) or ["other"]
                img = ImageInfo(
                    id=block.id,
                    block_id=block.block_id,
                    notebook_id=block.notebook_id,
                    notebook_slug=notebook.slug,
                    workspace_slug=workspace.slug,
                    title=block.title,
                    filename=block.filename,
                    content_type=block.content_type,
                    roles=roles,
                )
                for role in roles:
                    role_images.setdefault(role, []).append(img)
        finally:
            nb_session.close()

    # Order: default roles first, custom roles next, "other" last
    all_role_keys = list(role_images.keys())
    ordered = [r for r in DEFAULT_ROLES if r in all_role_keys]
    ordered += [r for r in all_role_keys if r not in DEFAULT_ROLES and r != "other"]
    if "other" in all_role_keys and "other" not in ordered:
        ordered.append("other")

    total = sum(len(imgs) for imgs in role_images.values())
    roles_list = [RoleGroup(role=r, images=role_images[r]) for r in ordered if role_images.get(r)]

    return ProjectDetail(slug=slug, name=_slug_to_name(slug), total_images=total, roles=roles_list)


@nested_router.post("/{slug}/assign")
async def assign_to_project(
    workspace_identifier: str,
    slug: str,
    request: AssignRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Add project:<slug> and project:<slug>:<role> tags to given blocks."""
    workspace = await get_workspace_by_slug(workspace_identifier, current_user, session)
    result = await session.execute(select(Notebook).where(Notebook.workspace_id == workspace.id))
    notebooks = result.scalars().all()
    workspace_path = Path(workspace.path).resolve()

    new_tags = [f"project:{slug}"] + [f"project:{slug}:{r}" for r in request.roles]
    remaining_ids = set(request.image_ids)
    updated = 0

    for notebook in notebooks:
        if not remaining_ids:
            break
        nb_path = workspace_path / notebook.path
        if not nb_path.exists():
            continue
        nb_session = get_notebook_session(str(nb_path))
        try:
            for block_id in list(remaining_ids):
                block = nb_session.execute(
                    select(Block).where(Block.notebook_id == notebook.id, Block.block_id == block_id)
                ).scalar_one_or_none()
                if not block:
                    continue
                existing = _parse_tags(block)
                merged = existing + [t for t in new_tags if t not in existing]
                update_block_properties(
                    notebook_path=nb_path,
                    notebook_id=notebook.id,
                    block_id=block_id,
                    properties={"tags": merged},
                    nb_session=nb_session,
                )
                remaining_ids.discard(block_id)
                updated += 1
        finally:
            nb_session.close()

    return {"message": f"Assigned {updated} images to project '{slug}'", "updated": updated}


@nested_router.delete("/{slug}/assign")
async def unassign_from_project(
    workspace_identifier: str,
    slug: str,
    request: UnassignRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Remove all project:<slug>* tags from given blocks."""
    workspace = await get_workspace_by_slug(workspace_identifier, current_user, session)
    result = await session.execute(select(Notebook).where(Notebook.workspace_id == workspace.id))
    notebooks = result.scalars().all()
    workspace_path = Path(workspace.path).resolve()

    prefix = f"project:{slug}"
    remaining_ids = set(request.image_ids)
    updated = 0

    for notebook in notebooks:
        if not remaining_ids:
            break
        nb_path = workspace_path / notebook.path
        if not nb_path.exists():
            continue
        nb_session = get_notebook_session(str(nb_path))
        try:
            for block_id in list(remaining_ids):
                block = nb_session.execute(
                    select(Block).where(Block.notebook_id == notebook.id, Block.block_id == block_id)
                ).scalar_one_or_none()
                if not block:
                    continue
                existing = _parse_tags(block)
                filtered = [t for t in existing if not t.startswith(prefix)]
                update_block_properties(
                    notebook_path=nb_path,
                    notebook_id=notebook.id,
                    block_id=block_id,
                    properties={"tags": filtered},
                    nb_session=nb_session,
                )
                remaining_ids.discard(block_id)
                updated += 1
        finally:
            nb_session.close()

    return {"message": f"Removed project '{slug}' tags from {updated} images", "updated": updated}
