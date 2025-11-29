"""Entries API routes."""

import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from codex.api.utils import get_workspace_path
from codex.core.entry import Entry as CoreEntry
from codex.core.page import Page as CorePage
from codex.core.workspace import Workspace
from codex.db.models import Artifact, Entry, Page

router = APIRouter()


def _entry_to_core(ws: Workspace, entry: Entry) -> CoreEntry:
    """Convert a db Entry model to a CoreEntry instance."""
    return CoreEntry.from_dict(ws, {
        "id": entry.id,
        "page_id": entry.page_id,
        "entry_type": entry.entry_type,
        "title": entry.title,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "status": entry.status,
        "parent_id": entry.parent_id,
        "inputs": json.loads(entry.inputs) if entry.inputs else {},
        "outputs": json.loads(entry.outputs) if entry.outputs else {},
        "execution": json.loads(entry.execution) if entry.execution else {},
        "metrics": json.loads(entry.metrics) if entry.metrics else {},
        "metadata": json.loads(entry.metadata_) if entry.metadata_ else {},
        "tags": [et.tag.name for et in entry.tags] if entry.tags else [],
    })


def _page_to_core(ws: Workspace, page: Page) -> CorePage:
    """Convert a db Page model to a CorePage instance."""
    return CorePage.from_dict(ws, {
        "id": page.id,
        "notebook_id": page.notebook_id,
        "title": page.title,
        "date": page.date.isoformat() if page.date else None,
        "created_at": page.created_at.isoformat() if page.created_at else None,
        "updated_at": page.updated_at.isoformat() if page.updated_at else None,
        "narrative": json.loads(page.narrative) if page.narrative else {},
        "tags": [pt.tag.name for pt in page.tags] if page.tags else [],
        "metadata": json.loads(page.metadata_) if page.metadata_ else {},
    })


class EntryCreateRequest(BaseModel):
    """Request model for creating an entry."""

    workspace_path: Optional[str] = None
    page_id: str
    entry_type: str
    title: str
    inputs: dict
    parent_id: Optional[str] = None
    tags: list[str] = []
    execute_immediately: bool = False


class EntryResponse(BaseModel):
    """Response model for entry."""

    id: str
    page_id: str
    entry_type: str
    title: str
    created_at: str
    status: str
    parent_id: Optional[str]
    inputs: dict
    outputs: dict
    execution: dict
    metrics: dict
    metadata: dict
    tags: list[str]


@router.post("", response_model=EntryResponse)
async def create_entry(request: EntryCreateRequest):
    """Create a new entry."""
    try:
        ws = Workspace.load(get_workspace_path(request.workspace_path))
        session = ws.db_manager.get_session()
        try:
            page = Page.get_by_id(session, request.page_id)
            if not page:
                raise HTTPException(status_code=404, detail="Page not found")

            core_page = _page_to_core(ws, page)
            entry = core_page.create_entry(
                entry_type=request.entry_type,
                title=request.title,
                inputs=request.inputs,
                parent_id=request.parent_id,
                tags=request.tags,
            )

            if request.execute_immediately:
                await entry.execute()

            return EntryResponse(
                id=entry.id,
                page_id=entry.page_id,
                entry_type=entry.entry_type,
                title=entry.title,
                created_at=entry.created_at.isoformat(),
                status=entry.status,
                parent_id=entry.parent_id,
                inputs=entry.inputs,
                outputs=entry.outputs,
                execution=entry.execution,
                metrics=entry.metrics,
                metadata=entry.metadata,
                tags=entry.tags,
            )
        finally:
            session.close()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entry_id}", response_model=EntryResponse)
async def get_entry(entry_id: str, workspace_path: Optional[str] = Query(None)):
    """Get entry details."""
    try:
        ws = Workspace.load(get_workspace_path(workspace_path))
        session = ws.db_manager.get_session()
        try:
            entry = Entry.get_by_id(session, entry_id)
            if not entry:
                raise HTTPException(status_code=404, detail="Entry not found")

            return EntryResponse(
                id=entry.id,
                page_id=entry.page_id,
                entry_type=entry.entry_type,
                title=entry.title,
                created_at=entry.created_at.isoformat() if entry.created_at else None,
                status=entry.status,
                parent_id=entry.parent_id,
                inputs=json.loads(entry.inputs) if entry.inputs else {},
                outputs=json.loads(entry.outputs) if entry.outputs else {},
                execution=json.loads(entry.execution) if entry.execution else {},
                metrics=json.loads(entry.metrics) if entry.metrics else {},
                metadata=json.loads(entry.metadata_) if entry.metadata_ else {},
                tags=[et.tag.name for et in entry.tags] if entry.tags else [],
            )
        finally:
            session.close()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class EntryExecuteRequest(BaseModel):
    """Request model for executing an entry."""

    workspace_path: Optional[str] = None


@router.post("/{entry_id}/execute", response_model=EntryResponse)
async def execute_entry(entry_id: str, request: EntryExecuteRequest):
    """Execute an entry."""
    try:
        ws = Workspace.load(get_workspace_path(request.workspace_path))
        session = ws.db_manager.get_session()
        try:
            entry = Entry.get_by_id(session, entry_id)
            if not entry:
                raise HTTPException(status_code=404, detail="Entry not found")

            core_entry = _entry_to_core(ws, entry)
            await core_entry.execute()

            return EntryResponse(
                id=core_entry.id,
                page_id=core_entry.page_id,
                entry_type=core_entry.entry_type,
                title=core_entry.title,
                created_at=core_entry.created_at.isoformat(),
                status=core_entry.status,
                parent_id=core_entry.parent_id,
                inputs=core_entry.inputs,
                outputs=core_entry.outputs,
                execution=core_entry.execution,
                metrics=core_entry.metrics,
                metadata=core_entry.metadata,
                tags=core_entry.tags,
            )
        finally:
            session.close()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class VariationCreateRequest(BaseModel):
    """Request model for creating a variation."""

    workspace_path: Optional[str] = None
    title: str
    input_overrides: dict
    tags: list[str] = []


@router.post("/{entry_id}/variations", response_model=EntryResponse)
async def create_variation(entry_id: str, request: VariationCreateRequest):
    """Create a variation of an entry."""
    try:
        ws = Workspace.load(get_workspace_path(request.workspace_path))
        session = ws.db_manager.get_session()
        try:
            entry = Entry.get_by_id(session, entry_id)
            if not entry:
                raise HTTPException(status_code=404, detail="Entry not found")

            core_entry = _entry_to_core(ws, entry)
            variation = core_entry.create_variation(
                title=request.title,
                input_overrides=request.input_overrides,
                tags=request.tags if request.tags else None,
            )

            return EntryResponse(
                id=variation.id,
                page_id=variation.page_id,
                entry_type=variation.entry_type,
                title=variation.title,
                created_at=variation.created_at.isoformat(),
                status=variation.status,
                parent_id=variation.parent_id,
                inputs=variation.inputs,
                outputs=variation.outputs,
                execution=variation.execution,
                metrics=variation.metrics,
                metadata=variation.metadata,
                tags=variation.tags,
            )
        finally:
            session.close()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entry_id}/lineage")
async def get_entry_lineage(
    entry_id: str,
    workspace_path: Optional[str] = Query(None),
    depth: int = Query(default=3, ge=1, le=10),
):
    """Get entry lineage graph."""
    try:
        ws = Workspace.load(get_workspace_path(workspace_path))
        session = ws.db_manager.get_session()
        try:
            entry = Entry.get_by_id(session, entry_id)
            if not entry:
                raise HTTPException(status_code=404, detail="Entry not found")

            core_entry = _entry_to_core(ws, entry)
            lineage = core_entry.get_lineage(depth)

            return lineage
        finally:
            session.close()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{entry_id}")
async def delete_entry(entry_id: str, workspace_path: Optional[str] = Query(None)):
    """Delete an entry."""
    try:
        ws = Workspace.load(get_workspace_path(workspace_path))
        session = ws.db_manager.get_session()
        try:
            entry = Entry.get_by_id(session, entry_id)
            if not entry:
                raise HTTPException(status_code=404, detail="Entry not found")

            core_entry = _entry_to_core(ws, entry)
            core_entry.delete()

            return {"message": "Entry deleted successfully"}
        finally:
            session.close()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entry_id}/artifacts")
async def list_entry_artifacts(entry_id: str, workspace_path: Optional[str] = Query(None)):
    """List artifacts for an entry."""
    try:
        ws = Workspace.load(get_workspace_path(workspace_path))
        session = ws.db_manager.get_session()
        try:
            entry = Entry.get_by_id(session, entry_id)
            if not entry:
                raise HTTPException(status_code=404, detail="Entry not found")

            artifacts = Artifact.find_by(session, entry_id=entry_id)
            return [
                {
                    "id": a.id,
                    "entry_id": a.entry_id,
                    "type": a.type,
                    "hash": a.hash,
                    "size_bytes": a.size_bytes,
                    "path": a.path,
                    "thumbnail_path": a.thumbnail_path,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                    "archived": a.archived,
                    "archive_strategy": a.archive_strategy,
                    "original_size_bytes": a.original_size_bytes,
                    "metadata": json.loads(a.metadata_) if a.metadata_ else {},
                }
                for a in artifacts
            ]
        finally:
            session.close()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
