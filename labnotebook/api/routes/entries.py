"""Entries API routes."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from labnotebook.core.workspace import Workspace

router = APIRouter()


class EntryCreateRequest(BaseModel):
    """Request model for creating an entry."""
    workspace_path: str
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
        ws = Workspace.load(Path(request.workspace_path))

        from labnotebook.core.page import Page
        page_data = ws.db_manager.get_page(request.page_id)
        if not page_data:
            raise HTTPException(status_code=404, detail="Page not found")

        page = Page.from_dict(ws, page_data)
        entry = page.create_entry(
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
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entry_id}", response_model=EntryResponse)
async def get_entry(entry_id: str, workspace_path: str = Query(...)):
    """Get entry details."""
    try:
        ws = Workspace.load(Path(workspace_path))
        entry_data = ws.db_manager.get_entry(entry_id)
        if not entry_data:
            raise HTTPException(status_code=404, detail="Entry not found")

        return EntryResponse(
            id=entry_data["id"],
            page_id=entry_data["page_id"],
            entry_type=entry_data["entry_type"],
            title=entry_data["title"],
            created_at=entry_data["created_at"],
            status=entry_data["status"],
            parent_id=entry_data.get("parent_id"),
            inputs=entry_data.get("inputs", {}),
            outputs=entry_data.get("outputs", {}),
            execution=entry_data.get("execution", {}),
            metrics=entry_data.get("metrics", {}),
            metadata=entry_data.get("metadata", {}),
            tags=entry_data.get("tags", []),
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class EntryExecuteRequest(BaseModel):
    """Request model for executing an entry."""
    workspace_path: str


@router.post("/{entry_id}/execute", response_model=EntryResponse)
async def execute_entry(entry_id: str, request: EntryExecuteRequest):
    """Execute an entry."""
    try:
        ws = Workspace.load(Path(request.workspace_path))

        from labnotebook.core.entry import Entry
        entry_data = ws.db_manager.get_entry(entry_id)
        if not entry_data:
            raise HTTPException(status_code=404, detail="Entry not found")

        entry = Entry.from_dict(ws, entry_data)
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
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class VariationCreateRequest(BaseModel):
    """Request model for creating a variation."""
    workspace_path: str
    title: str
    input_overrides: dict
    tags: list[str] = []


@router.post("/{entry_id}/variations", response_model=EntryResponse)
async def create_variation(entry_id: str, request: VariationCreateRequest):
    """Create a variation of an entry."""
    try:
        ws = Workspace.load(Path(request.workspace_path))

        from labnotebook.core.entry import Entry
        entry_data = ws.db_manager.get_entry(entry_id)
        if not entry_data:
            raise HTTPException(status_code=404, detail="Entry not found")

        entry = Entry.from_dict(ws, entry_data)
        variation = entry.create_variation(
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
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entry_id}/lineage")
async def get_entry_lineage(
    entry_id: str,
    workspace_path: str = Query(...),
    depth: int = Query(default=3, ge=1, le=10),
):
    """Get entry lineage graph."""
    try:
        ws = Workspace.load(Path(workspace_path))

        from labnotebook.core.entry import Entry
        entry_data = ws.db_manager.get_entry(entry_id)
        if not entry_data:
            raise HTTPException(status_code=404, detail="Entry not found")

        entry = Entry.from_dict(ws, entry_data)
        lineage = entry.get_lineage(depth)

        return lineage
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{entry_id}")
async def delete_entry(entry_id: str, workspace_path: str = Query(...)):
    """Delete an entry."""
    try:
        ws = Workspace.load(Path(workspace_path))

        from labnotebook.core.entry import Entry
        entry_data = ws.db_manager.get_entry(entry_id)
        if not entry_data:
            raise HTTPException(status_code=404, detail="Entry not found")

        entry = Entry.from_dict(ws, entry_data)
        entry.delete()

        return {"message": "Entry deleted successfully"}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entry_id}/artifacts")
async def list_entry_artifacts(entry_id: str, workspace_path: str = Query(...)):
    """List artifacts for an entry."""
    try:
        ws = Workspace.load(Path(workspace_path))

        entry_data = ws.db_manager.get_entry(entry_id)
        if not entry_data:
            raise HTTPException(status_code=404, detail="Entry not found")

        artifacts = ws.db_manager.list_artifacts(entry_id)
        return artifacts
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
