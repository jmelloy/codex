"""Pages API routes."""

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.auth import get_current_user_workspace
from core.page import Page as CorePage
from core.workspace import Workspace
from db.models import Page

router = APIRouter()


def _page_to_core(ws: Workspace, page: Page) -> CorePage:
    """Convert a db Page model to a CorePage instance."""
    return CorePage.from_dict(
        ws,
        {
            "id": page.id,
            "notebook_id": page.notebook_id,
            "title": page.title,
            "date": page.date.isoformat() if page.date else None,
            "created_at": page.created_at.isoformat() if page.created_at else None,
            "updated_at": page.updated_at.isoformat() if page.updated_at else None,
            "narrative": json.loads(page.narrative) if page.narrative else {},
            "tags": [pt.tag.name for pt in page.tags] if page.tags else [],
            "metadata": json.loads(page.metadata_) if page.metadata_ else {},
        },
    )


class PageCreateRequest(BaseModel):
    """Request model for creating a page."""

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
async def create_page(
    request: PageCreateRequest,
    ws: Workspace = Depends(get_current_user_workspace),
):
    """Create a new page."""
    try:
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
async def get_page(
    page_id: str,
    ws: Workspace = Depends(get_current_user_workspace),
):
    """Get page details."""
    try:
        session = ws.db_manager.get_session()
        try:
            page = Page.get_by_id(session, page_id)
            if not page:
                raise HTTPException(status_code=404, detail="Page not found")

            return PageResponse(
                id=page.id,
                notebook_id=page.notebook_id,
                title=page.title,
                date=page.date.isoformat() if page.date else None,
                created_at=page.created_at.isoformat() if page.created_at else None,
                updated_at=page.updated_at.isoformat() if page.updated_at else None,
                narrative=json.loads(page.narrative) if page.narrative else {},
                tags=[pt.tag.name for pt in page.tags] if page.tags else [],
                metadata=json.loads(page.metadata_) if page.metadata_ else {},
            )
        finally:
            session.close()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PageUpdateRequest(BaseModel):
    """Request model for updating a page."""

    title: Optional[str] = None
    date: Optional[str] = None
    narrative: Optional[dict] = None
    tags: Optional[list[str]] = None
    metadata: Optional[dict] = None


@router.patch("/{page_id}", response_model=PageResponse)
async def update_page(
    page_id: str,
    request: PageUpdateRequest,
    ws: Workspace = Depends(get_current_user_workspace),
):
    """Update a page."""
    try:
        session = ws.db_manager.get_session()
        try:
            page = Page.get_by_id(session, page_id)
            if not page:
                raise HTTPException(status_code=404, detail="Page not found")

            core_page = _page_to_core(ws, page)

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

            core_page.update(**update_data)

            return PageResponse(
                id=core_page.id,
                notebook_id=core_page.notebook_id,
                title=core_page.title,
                date=core_page.date.isoformat() if core_page.date else None,
                created_at=core_page.created_at.isoformat(),
                updated_at=core_page.updated_at.isoformat(),
                narrative=core_page.narrative,
                tags=core_page.tags,
                metadata=core_page.metadata,
            )
        finally:
            session.close()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class NarrativeUpdateRequest(BaseModel):
    """Request model for updating page narrative."""

    field: str
    content: str


@router.patch("/{page_id}/narrative", response_model=PageResponse)
async def update_narrative(
    page_id: str,
    request: NarrativeUpdateRequest,
    ws: Workspace = Depends(get_current_user_workspace),
):
    """Update page narrative field."""
    try:
        session = ws.db_manager.get_session()
        try:
            page = Page.get_by_id(session, page_id)
            if not page:
                raise HTTPException(status_code=404, detail="Page not found")

            core_page = _page_to_core(ws, page)
            core_page.update_narrative(request.field, request.content)

            return PageResponse(
                id=core_page.id,
                notebook_id=core_page.notebook_id,
                title=core_page.title,
                date=core_page.date.isoformat() if core_page.date else None,
                created_at=core_page.created_at.isoformat(),
                updated_at=core_page.updated_at.isoformat(),
                narrative=core_page.narrative,
                tags=core_page.tags,
                metadata=core_page.metadata,
            )
        finally:
            session.close()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{page_id}")
async def delete_page(
    page_id: str,
    ws: Workspace = Depends(get_current_user_workspace),
):
    """Delete a page."""
    try:
        session = ws.db_manager.get_session()
        try:
            page = Page.get_by_id(session, page_id)
            if not page:
                raise HTTPException(status_code=404, detail="Page not found")

            core_page = _page_to_core(ws, page)
            core_page.delete()

            return {"message": "Page deleted successfully"}
        finally:
            session.close()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{page_id}/entries")
async def list_page_entries(
    page_id: str,
    ws: Workspace = Depends(get_current_user_workspace),
):
    """List entries in a page."""
    try:
        session = ws.db_manager.get_session()
        try:
            page = Page.get_by_id(session, page_id)
            if not page:
                raise HTTPException(status_code=404, detail="Page not found")

            core_page = _page_to_core(ws, page)
            entries = core_page.list_entries()

            return [
                {
                    "id": entry.id,
                    "page_id": entry.page_id,
                    "entry_type": entry.entry_type,
                    "title": entry.title,
                    "created_at": entry.created_at.isoformat(),
                    "status": entry.status,
                    "parent_id": entry.parent_id,
                    "inputs": entry.inputs,
                    "outputs": entry.outputs,
                    "execution": entry.execution,
                    "metrics": entry.metrics,
                    "metadata": entry.metadata,
                    "tags": entry.tags,
                }
                for entry in entries
            ]
        finally:
            session.close()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
