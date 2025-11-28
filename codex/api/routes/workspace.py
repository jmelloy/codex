"""Workspace API routes."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from codex.core.workspace import Workspace

router = APIRouter()


class WorkspaceInitRequest(BaseModel):
    """Request model for workspace initialization."""
    path: str
    name: str


class WorkspaceResponse(BaseModel):
    """Response model for workspace info."""
    path: str
    name: str
    version: str
    created_at: str


@router.post("/workspace/init", response_model=WorkspaceResponse)
async def init_workspace(request: WorkspaceInitRequest):
    """Initialize a new workspace."""
    try:
        ws = Workspace.initialize(Path(request.path), request.name)
        config = ws.get_config()
        return WorkspaceResponse(
            path=str(ws.path),
            name=config.get("name", request.name),
            version=config.get("version", "1.0.0"),
            created_at=config.get("created_at", ""),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspace")
async def get_workspace(workspace_path: str):
    """Get workspace info."""
    try:
        ws = Workspace.load(Path(workspace_path))
        config = ws.get_config()
        return {
            "path": str(ws.path),
            "name": config.get("name", ""),
            "version": config.get("version", "1.0.0"),
            "created_at": config.get("created_at", ""),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
