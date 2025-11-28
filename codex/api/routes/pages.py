"""Pages API routes."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from codex.core.workspace import Workspace

router = APIRouter()


class PageCreateRequest(BaseModel):
    """Request model for creating a page."""
    workspace_path: str
    notebook_id: str
    title: str
    date: Optional[str] = None
    narrative: Optional[dict] = None


class PageResponse(BaseModel):
    """Response model for page."""
    id: str
    notebook_id: str
    title: str
    date: Optional[str]
    created_at: str
    updated_at: str
    narrative: dict
    tags: list[str]
    metadata: dict


@router.post("", response_model=PageResponse)
async def create_page(request: PageCreateRequest):
    """Create a new page."""
    try:
        ws = Workspace.load(Path(request.workspace_path))
        notebook = ws.get_notebook(request.notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        page_date = datetime.fromisoformat(request.date) if request.date else None
        page = notebook.create_page(
            title=request.title,
            date=page_date,
            narrative=request.narrative,
        )

        return PageResponse(
            id=page.id,
            notebook_id=page.notebook_id,
            title=page.title,
            date=page.date.isoformat() if page.date else None,
            created_at=page.created_at.isoformat(),
            updated_at=page.updated_at.isoformat(),
            narrative=page.narrative,
            tags=page.tags,
            metadata=page.metadata,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{page_id}", response_model=PageResponse)
async def get_page(page_id: str, workspace_path: str = Query(...)):
    """Get page details."""
    try:
        ws = Workspace.load(Path(workspace_path))
        page_data = ws.db_manager.get_page(page_id)
        if not page_data:
            raise HTTPException(status_code=404, detail="Page not found")

        return PageResponse(
            id=page_data["id"],
            notebook_id=page_data["notebook_id"],
            title=page_data["title"],
            date=page_data.get("date"),
            created_at=page_data["created_at"],
            updated_at=page_data["updated_at"],
            narrative=page_data.get("narrative", {}),
            tags=page_data.get("tags", []),
            metadata=page_data.get("metadata", {}),
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PageUpdateRequest(BaseModel):
    """Request model for updating a page."""
    workspace_path: str
    title: Optional[str] = None
    date: Optional[str] = None
    narrative: Optional[dict] = None
    tags: Optional[list[str]] = None
    metadata: Optional[dict] = None


@router.patch("/{page_id}", response_model=PageResponse)
async def update_page(page_id: str, request: PageUpdateRequest):
    """Update a page."""
    try:
        ws = Workspace.load(Path(request.workspace_path))

        from codex.core.page import Page
        page_data = ws.db_manager.get_page(page_id)
        if not page_data:
            raise HTTPException(status_code=404, detail="Page not found")

        page = Page.from_dict(ws, page_data)

        update_data = {}
        if request.title is not None:
            update_data["title"] = request.title
        if request.date is not None:
            update_data["date"] = datetime.fromisoformat(request.date)
        if request.narrative is not None:
            update_data["narrative"] = request.narrative
        if request.tags is not None:
            update_data["tags"] = request.tags
        if request.metadata is not None:
            update_data["metadata"] = request.metadata

        page.update(**update_data)

        return PageResponse(
            id=page.id,
            notebook_id=page.notebook_id,
            title=page.title,
            date=page.date.isoformat() if page.date else None,
            created_at=page.created_at.isoformat(),
            updated_at=page.updated_at.isoformat(),
            narrative=page.narrative,
            tags=page.tags,
            metadata=page.metadata,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class NarrativeUpdateRequest(BaseModel):
    """Request model for updating page narrative."""
    workspace_path: str
    field: str
    content: str


@router.patch("/{page_id}/narrative", response_model=PageResponse)
async def update_narrative(page_id: str, request: NarrativeUpdateRequest):
    """Update page narrative field."""
    try:
        ws = Workspace.load(Path(request.workspace_path))

        from codex.core.page import Page
        page_data = ws.db_manager.get_page(page_id)
        if not page_data:
            raise HTTPException(status_code=404, detail="Page not found")

        page = Page.from_dict(ws, page_data)
        page.update_narrative(request.field, request.content)

        return PageResponse(
            id=page.id,
            notebook_id=page.notebook_id,
            title=page.title,
            date=page.date.isoformat() if page.date else None,
            created_at=page.created_at.isoformat(),
            updated_at=page.updated_at.isoformat(),
            narrative=page.narrative,
            tags=page.tags,
            metadata=page.metadata,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{page_id}")
async def delete_page(page_id: str, workspace_path: str = Query(...)):
    """Delete a page."""
    try:
        ws = Workspace.load(Path(workspace_path))

        from codex.core.page import Page
        page_data = ws.db_manager.get_page(page_id)
        if not page_data:
            raise HTTPException(status_code=404, detail="Page not found")

        page = Page.from_dict(ws, page_data)
        page.delete()

        return {"message": "Page deleted successfully"}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{page_id}/entries")
async def list_page_entries(page_id: str, workspace_path: str = Query(...)):
    """List entries in a page."""
    try:
        ws = Workspace.load(Path(workspace_path))

        from codex.core.page import Page
        page_data = ws.db_manager.get_page(page_id)
        if not page_data:
            raise HTTPException(status_code=404, detail="Page not found")

        page = Page.from_dict(ws, page_data)
        entries = page.list_entries()

        return [
            {
                "id": entry.id,
                "page_id": entry.page_id,
                "entry_type": entry.entry_type,
                "title": entry.title,
                "created_at": entry.created_at.isoformat(),
                "status": entry.status,
                "parent_id": entry.parent_id,
                "tags": entry.tags,
            }
            for entry in entries
        ]
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
