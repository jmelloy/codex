"""Notebooks API routes."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from codex.api.utils import get_workspace_path
from codex.core.workspace import Workspace

router = APIRouter()


class NotebookCreateRequest(BaseModel):
    """Request model for creating a notebook."""

    workspace_path: Optional[str] = None
    title: str
    description: str = ""
    tags: list[str] = []


class NotebookResponse(BaseModel):
    """Response model for notebook."""

    id: str
    title: str
    description: str
    created_at: str
    updated_at: str
    tags: list[str]
    settings: dict
    metadata: dict


@router.post("", response_model=NotebookResponse)
async def create_notebook(request: NotebookCreateRequest):
    """Create a new notebook."""
    try:
        ws = Workspace.load(get_workspace_path(request.workspace_path))
        notebook = ws.create_notebook(
            title=request.title,
            description=request.description,
            tags=request.tags,
        )
        return NotebookResponse(
            id=notebook.id,
            title=notebook.title,
            description=notebook.description,
            created_at=notebook.created_at.isoformat(),
            updated_at=notebook.updated_at.isoformat(),
            tags=notebook.tags,
            settings=notebook.settings,
            metadata=notebook.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_notebooks(workspace_path: Optional[str] = Query(None)):
    """List all notebooks in workspace."""
    try:
        ws = Workspace.load(get_workspace_path(workspace_path))
        notebooks = ws.list_notebooks()
        return [
            {
                "id": nb.id,
                "title": nb.title,
                "description": nb.description,
                "created_at": nb.created_at.isoformat(),
                "updated_at": nb.updated_at.isoformat(),
                "tags": nb.tags,
            }
            for nb in notebooks
        ]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{notebook_id}", response_model=NotebookResponse)
async def get_notebook(notebook_id: str, workspace_path: Optional[str] = Query(None)):
    """Get notebook details."""
    try:
        ws = Workspace.load(get_workspace_path(workspace_path))
        notebook = ws.get_notebook(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")
        return NotebookResponse(
            id=notebook.id,
            title=notebook.title,
            description=notebook.description,
            created_at=notebook.created_at.isoformat(),
            updated_at=notebook.updated_at.isoformat(),
            tags=notebook.tags,
            settings=notebook.settings,
            metadata=notebook.metadata,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class NotebookUpdateRequest(BaseModel):
    """Request model for updating a notebook."""

    workspace_path: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    settings: Optional[dict] = None
    metadata: Optional[dict] = None


@router.patch("/{notebook_id}", response_model=NotebookResponse)
async def update_notebook(notebook_id: str, request: NotebookUpdateRequest):
    """Update a notebook."""
    try:
        ws = Workspace.load(get_workspace_path(request.workspace_path))
        notebook = ws.get_notebook(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        update_data = {}
        if request.title is not None:
            update_data["title"] = request.title
        if request.description is not None:
            update_data["description"] = request.description
        if request.tags is not None:
            update_data["tags"] = request.tags
        if request.settings is not None:
            update_data["settings"] = request.settings
        if request.metadata is not None:
            update_data["metadata"] = request.metadata

        notebook.update(**update_data)

        return NotebookResponse(
            id=notebook.id,
            title=notebook.title,
            description=notebook.description,
            created_at=notebook.created_at.isoformat(),
            updated_at=notebook.updated_at.isoformat(),
            tags=notebook.tags,
            settings=notebook.settings,
            metadata=notebook.metadata,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{notebook_id}")
async def delete_notebook(
    notebook_id: str, workspace_path: Optional[str] = Query(None)
):
    """Delete a notebook."""
    try:
        ws = Workspace.load(get_workspace_path(workspace_path))
        notebook = ws.get_notebook(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        notebook.delete()
        return {"message": "Notebook deleted successfully"}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{notebook_id}/pages")
async def list_notebook_pages(
    notebook_id: str, workspace_path: Optional[str] = Query(None)
):
    """List pages in a notebook."""
    try:
        ws = Workspace.load(get_workspace_path(workspace_path))
        notebook = ws.get_notebook(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        pages = notebook.list_pages()
        return [
            {
                "id": page.id,
                "notebook_id": page.notebook_id,
                "title": page.title,
                "date": page.date.isoformat() if page.date else None,
                "created_at": page.created_at.isoformat(),
                "updated_at": page.updated_at.isoformat(),
                "narrative": page.narrative,
                "tags": page.tags,
            }
            for page in pages
        ]
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
