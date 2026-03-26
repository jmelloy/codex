"""Search routes with hybrid FTS + vector search."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from codex.api.auth import get_current_active_user
from codex.api.routes.notebooks import get_notebook_by_slug
from codex.api.routes.workspaces import get_workspace_by_slug
from codex.api.schemas import (
    NotebookSearchResponse,
    NotebookTagSearchResponse,
    SearchResultResponse,
    WorkspaceSearchResponse,
    WorkspaceTagSearchResponse,
)
from codex.db.database import get_notebook_engine, get_notebook_session, get_system_session
from codex.db.models import Block, Notebook, User

logger = logging.getLogger(__name__)

# New nested router for workspace-based search routes
nested_router = APIRouter()


def _search_notebook_blocks(
    notebook_path: str,
    notebook_id: int,
    query: str,
    limit: int = 20,
) -> list[SearchResultResponse]:
    """Run hybrid search on a single notebook and return results."""
    from codex.core.vectorizer import ensure_search_tables, hybrid_search

    engine = get_notebook_engine(notebook_path)

    try:
        ensure_search_tables(engine)
    except Exception as e:
        logger.warning(f"Could not initialise search tables for {notebook_path}: {e}")
        return _fallback_search(notebook_path, notebook_id, query, limit)

    try:
        ranked = hybrid_search(engine, query, limit=limit)
    except Exception as e:
        logger.warning(f"Hybrid search failed for {notebook_path}: {e}")
        return _fallback_search(notebook_path, notebook_id, query, limit)

    if not ranked:
        return _fallback_search(notebook_path, notebook_id, query, limit)

    # Resolve block_ids to Block models
    session = get_notebook_session(notebook_path)
    try:
        block_ids = [bid for bid, _ in ranked]
        score_map = {bid: score for bid, score in ranked}
        blocks = session.execute(
            select(Block).where(Block.notebook_id == notebook_id, Block.block_id.in_(block_ids))
        ).scalars().all()
        block_map = {b.block_id: b for b in blocks}

        results = []
        for bid in block_ids:
            block = block_map.get(bid)
            if not block:
                continue
            results.append(
                SearchResultResponse(
                    id=block.id,
                    path=block.path,
                    filename=block.filename,
                    title=block.title,
                    description=block.description,
                    content_type=block.content_type,
                    notebook_id=block.notebook_id,
                    snippet=block.description or block.title or block.path,
                    score=round(score_map.get(bid, 0.0), 4),
                )
            )
        return results
    finally:
        session.close()


def _fallback_search(
    notebook_path: str,
    notebook_id: int,
    query: str,
    limit: int = 20,
) -> list[SearchResultResponse]:
    """Fallback: simple LIKE search on page title + properties + description."""
    session = get_notebook_session(notebook_path)
    try:
        pattern = f"%{query}%"
        stmt = (
            select(Block)
            .where(
                Block.notebook_id == notebook_id,
                Block.block_type == "page",
            )
            .where(
                Block.title.ilike(pattern)
                | Block.description.ilike(pattern)
                | Block.properties.ilike(pattern)
            )
            .limit(limit)
        )
        blocks = session.execute(stmt).scalars().all()
        results = []
        for block in blocks:
            results.append(
                SearchResultResponse(
                    id=block.id,
                    path=block.path,
                    filename=block.filename,
                    title=block.title,
                    description=block.description,
                    content_type=block.content_type,
                    notebook_id=block.notebook_id,
                    snippet=block.description or block.title or block.path,
                    score=1.0,
                )
            )
        return results
    finally:
        session.close()


def _search_tags_in_notebook(
    notebook_path: str,
    notebook_id: int,
    tag_list: list[str],
    limit: int = 50,
) -> list[SearchResultResponse]:
    """Search blocks by tags in a single notebook."""
    from codex.db.models.notebook import BlockTag, Tag

    session = get_notebook_session(notebook_path)
    try:
        # Find blocks that have any of the requested tags
        stmt = (
            select(Block)
            .join(BlockTag, BlockTag.block_id == Block.id)
            .join(Tag, Tag.id == BlockTag.tag_id)
            .where(Block.notebook_id == notebook_id, Tag.name.in_(tag_list))
            .distinct()
            .limit(limit)
        )
        blocks = session.execute(stmt).scalars().all()
        results = []
        for block in blocks:
            results.append(
                SearchResultResponse(
                    id=block.id,
                    path=block.path,
                    filename=block.filename,
                    title=block.title,
                    description=block.description,
                    content_type=block.content_type,
                    notebook_id=block.notebook_id,
                    snippet=block.description or block.title or block.path,
                    score=1.0,
                )
            )
        return results
    finally:
        session.close()


@nested_router.get("/", response_model=WorkspaceSearchResponse)
async def search_workspace(
    workspace_identifier: str,
    q: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Search pages and content in a workspace (all notebooks)."""
    workspace = await get_workspace_by_slug(workspace_identifier, current_user, session)

    # Get all notebooks in workspace
    result = await session.execute(select(Notebook).where(Notebook.workspace_id == workspace.id))
    notebooks = result.scalars().all()

    all_results: list[SearchResultResponse] = []
    workspace_path = Path(workspace.path).resolve()

    for notebook in notebooks:
        nb_path = str(workspace_path / notebook.path)
        if not Path(nb_path).exists():
            continue
        try:
            results = _search_notebook_blocks(nb_path, notebook.id, q, limit=20)
            all_results.extend(results)
        except Exception as e:
            logger.warning(f"Search failed for notebook {notebook.slug}: {e}")

    # Sort by score descending and limit
    all_results.sort(key=lambda r: r.score or 0.0, reverse=True)
    all_results = all_results[:50]

    return WorkspaceSearchResponse(
        query=q,
        workspace_id=workspace.id,
        workspace_slug=workspace.slug,
        results=all_results,
    )


@nested_router.get("/tags", response_model=WorkspaceTagSearchResponse)
async def search_workspace_by_tags(
    workspace_identifier: str,
    tags: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Search files by tags in a workspace (all notebooks)."""
    workspace = await get_workspace_by_slug(workspace_identifier, current_user, session)
    tag_list = [tag.strip() for tag in tags.split(",")]

    result = await session.execute(select(Notebook).where(Notebook.workspace_id == workspace.id))
    notebooks = result.scalars().all()

    all_results: list[SearchResultResponse] = []
    workspace_path = Path(workspace.path).resolve()

    for notebook in notebooks:
        nb_path = str(workspace_path / notebook.path)
        if not Path(nb_path).exists():
            continue
        try:
            results = _search_tags_in_notebook(nb_path, notebook.id, tag_list)
            all_results.extend(results)
        except Exception as e:
            logger.warning(f"Tag search failed for notebook {notebook.slug}: {e}")

    return WorkspaceTagSearchResponse(
        tags=tag_list,
        workspace_id=workspace.id,
        workspace_slug=workspace.slug,
        results=all_results,
    )


# Notebook-level nested router
notebook_nested_router = APIRouter()


@notebook_nested_router.get("/", response_model=NotebookSearchResponse)
async def search_notebook(
    workspace_identifier: str,
    notebook_identifier: str,
    q: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Search files and content in a specific notebook."""
    workspace = await get_workspace_by_slug(workspace_identifier, current_user, session)
    notebook = await get_notebook_by_slug(notebook_identifier, workspace, session)

    workspace_path = Path(workspace.path).resolve()
    nb_path = str(workspace_path / notebook.path)

    results = _search_notebook_blocks(nb_path, notebook.id, q, limit=50)

    return NotebookSearchResponse(
        query=q,
        workspace_id=workspace.id,
        workspace_slug=workspace.slug,
        notebook_id=notebook.id,
        notebook_slug=notebook.slug,
        results=results,
    )


@notebook_nested_router.get("/tags", response_model=NotebookTagSearchResponse)
async def search_notebook_by_tags(
    workspace_identifier: str,
    notebook_identifier: str,
    tags: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Search files by tags in a specific notebook."""
    workspace = await get_workspace_by_slug(workspace_identifier, current_user, session)
    notebook = await get_notebook_by_slug(notebook_identifier, workspace, session)

    tag_list = [tag.strip() for tag in tags.split(",")]
    workspace_path = Path(workspace.path).resolve()
    nb_path = str(workspace_path / notebook.path)

    results = _search_tags_in_notebook(nb_path, notebook.id, tag_list)

    return NotebookTagSearchResponse(
        tags=tag_list,
        workspace_id=workspace.id,
        workspace_slug=workspace.slug,
        notebook_id=notebook.id,
        notebook_slug=notebook.slug,
        results=results,
    )


# ---------------------------------------------------------------------------
# Vectorization management endpoints
# ---------------------------------------------------------------------------

vectorize_router = APIRouter()


@vectorize_router.post("/workspaces/{workspace_identifier}/notebooks/{notebook_identifier}/vectorize")
async def vectorize_notebook(
    workspace_identifier: str,
    notebook_identifier: str,
    reset: bool = False,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Trigger vectorization of all pages in a notebook.

    Pass ?reset=true to drop and recreate the embeddings table first
    (needed after changing embedding model or dimensions).
    """
    from codex.core.vectorizer import reset_embedding_table, vectorize_all_pages

    workspace = await get_workspace_by_slug(workspace_identifier, current_user, session)
    notebook = await get_notebook_by_slug(notebook_identifier, workspace, session)

    workspace_path = Path(workspace.path).resolve()
    nb_path = str(workspace_path / notebook.path)

    engine = get_notebook_engine(nb_path)

    if reset:
        reset_embedding_table(engine)

    nb_session = get_notebook_session(nb_path)
    try:
        count = vectorize_all_pages(engine, notebook.id, nb_path, nb_session)
    finally:
        nb_session.close()

    return {"status": "ok", "pages_vectorized": count, "notebook": notebook.slug, "reset": reset}
