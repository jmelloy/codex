"""Artifacts API routes."""

import io
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from codex.core.workspace import Workspace

router = APIRouter()


class ArtifactUploadRequest(BaseModel):
    """Request model for uploading an artifact."""
    workspace_path: str
    entry_id: str
    metadata: Optional[str] = None


@router.post("")
async def upload_artifact(
    workspace_path: str,
    entry_id: str,
    file: UploadFile = File(...),
    metadata: Optional[str] = None,
):
    """Upload artifact to entry."""
    import json

    try:
        ws = Workspace.load(Path(workspace_path))

        from codex.core.entry import Entry
        entry_data = ws.db_manager.get_entry(entry_id)
        if not entry_data:
            raise HTTPException(status_code=404, detail="Entry not found")

        entry = Entry.from_dict(ws, entry_data)

        data = await file.read()
        artifact_metadata = json.loads(metadata) if metadata else {}

        artifact = entry.add_artifact(
            artifact_type=file.content_type or "application/octet-stream",
            data=data,
            metadata=artifact_metadata,
        )

        return artifact
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{artifact_hash}")
async def get_artifact(
    artifact_hash: str,
    workspace_path: str = Query(...),
    thumbnail: bool = Query(default=False),
):
    """Retrieve artifact by hash."""
    try:
        ws = Workspace.load(Path(workspace_path))

        if thumbnail:
            data = ws.storage_manager.get_thumbnail(artifact_hash)
            if not data:
                raise HTTPException(status_code=404, detail="Thumbnail not found")
            media_type = "image/jpeg"
        else:
            data = ws.storage_manager.retrieve(artifact_hash)
            if not data:
                raise HTTPException(status_code=404, detail="Artifact not found")

            artifact = ws.db_manager.get_artifact_by_hash(artifact_hash)
            media_type = artifact["type"] if artifact else "application/octet-stream"

        return StreamingResponse(
            io.BytesIO(data),
            media_type=media_type,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{artifact_hash}/info")
async def get_artifact_info(
    artifact_hash: str,
    workspace_path: str = Query(...),
):
    """Get artifact metadata."""
    try:
        ws = Workspace.load(Path(workspace_path))

        artifact = ws.db_manager.get_artifact_by_hash(artifact_hash)
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")

        return artifact
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
