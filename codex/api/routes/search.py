"""Search API routes."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from codex.core.workspace import Workspace

router = APIRouter()


class SearchRequest(BaseModel):
    """Request model for search."""
    workspace_path: str
    query: Optional[str] = None
    entry_type: Optional[str] = None
    tags: Optional[list[str]] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    notebook_id: Optional[str] = None
    page_id: Optional[str] = None


@router.post("")
async def search(request: SearchRequest):
    """Search entries."""
    try:
        ws = Workspace.load(Path(request.workspace_path))

        results = ws.search_entries(
            query=request.query,
            entry_type=request.entry_type,
            tags=request.tags,
            date_from=datetime.fromisoformat(request.date_from) if request.date_from else None,
            date_to=datetime.fromisoformat(request.date_to) if request.date_to else None,
            notebook_id=request.notebook_id,
            page_id=request.page_id,
        )

        return {
            "results": results,
            "count": len(results),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def search_get(
    workspace_path: str = Query(...),
    query: Optional[str] = None,
    entry_type: Optional[str] = None,
    notebook_id: Optional[str] = None,
    page_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """Search entries (GET method)."""
    try:
        ws = Workspace.load(Path(workspace_path))

        results = ws.search_entries(
            query=query,
            entry_type=entry_type,
            date_from=datetime.fromisoformat(date_from) if date_from else None,
            date_to=datetime.fromisoformat(date_to) if date_to else None,
            notebook_id=notebook_id,
            page_id=page_id,
        )

        return {
            "results": results,
            "count": len(results),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
