"""Workspace API routes."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from codex.api.utils import get_workspace_path
from codex.core.workspace import Workspace
from codex.integrations import IntegrationRegistry

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
async def get_workspace(workspace_path: Optional[str] = Query(None)):
    """Get workspace info."""
    try:
        ws = Workspace.load(get_workspace_path(workspace_path))
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


@router.get("/integrations")
async def list_integrations():
    """List all available integration types."""
    integrations = IntegrationRegistry.list_integrations()
    return {
        "integrations": integrations,
        "count": len(integrations),
    }


@router.get("/files/notebooks")
async def list_notebooks_files(workspace_path: Optional[str] = Query(None)):
    """List all files in the notebooks directory."""
    try:
        ws = Workspace.load(get_workspace_path(workspace_path))
        files = ws.scan_notebooks_directory()
        return {
            "path": str(ws.notebooks_path),
            "files": files,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/artifacts")
async def list_artifacts_files(workspace_path: Optional[str] = Query(None)):
    """List all files in the artifacts directory."""
    try:
        ws = Workspace.load(get_workspace_path(workspace_path))
        files = ws.scan_artifacts_directory()
        return {
            "path": str(ws.artifacts_path),
            "files": files,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/notebooks/content")
async def get_notebook_file_content(
    path: str = Query(..., description="Relative path to the file"),
    workspace_path: Optional[str] = Query(None),
):
    """Get the content of a file from the notebooks directory."""
    import mimetypes

    from fastapi.responses import FileResponse

    try:
        ws = Workspace.load(get_workspace_path(workspace_path))

        # Sanitize path to prevent directory traversal
        safe_path = Path(path).as_posix()
        if ".." in safe_path or safe_path.startswith("/"):
            raise HTTPException(status_code=400, detail="Invalid file path")

        file_path = ws.notebooks_path / safe_path

        # Ensure the file is within the notebooks directory
        try:
            file_path.resolve().relative_to(ws.notebooks_path.resolve())
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid file path")

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")

        # Determine content type
        content_type, _ = mimetypes.guess_type(str(file_path))
        if content_type is None:
            content_type = "application/octet-stream"

        return FileResponse(
            path=str(file_path),
            media_type=content_type,
            filename=file_path.name,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/artifacts/content")
async def get_artifact_file_content(
    path: str = Query(..., description="Relative path to the file"),
    workspace_path: Optional[str] = Query(None),
):
    """Get the content of a file from the artifacts directory."""
    import mimetypes

    from fastapi.responses import FileResponse

    try:
        ws = Workspace.load(get_workspace_path(workspace_path))

        # Sanitize path to prevent directory traversal
        safe_path = Path(path).as_posix()
        if ".." in safe_path or safe_path.startswith("/"):
            raise HTTPException(status_code=400, detail="Invalid file path")

        file_path = ws.artifacts_path / safe_path

        # Ensure the file is within the artifacts directory
        try:
            file_path.resolve().relative_to(ws.artifacts_path.resolve())
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid file path")

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")

        # Determine content type
        content_type, _ = mimetypes.guess_type(str(file_path))
        if content_type is None:
            content_type = "application/octet-stream"

        return FileResponse(
            path=str(file_path),
            media_type=content_type,
            filename=file_path.name,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
