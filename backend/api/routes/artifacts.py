"""Artifacts API routes."""

import io
import json
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.utils import get_workspace_path
from core.entry import Entry as CoreEntry
from core.workspace import Workspace
from db.models import Artifact, Entry

router = APIRouter()


def _entry_to_core(ws: Workspace, entry: Entry) -> CoreEntry:
    """Convert a db Entry model to a CoreEntry instance."""
    return CoreEntry.from_dict(
        ws,
        {
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
        },
    )


class ArtifactUploadRequest(BaseModel):
    """Request model for uploading an artifact."""

    workspace_path: Optional[str] = None
    entry_id: str
    metadata: Optional[str] = None


@router.post("")
async def upload_artifact(
    workspace_path: Optional[str] = None,
    entry_id: str = Query(...),
    file: UploadFile = File(...),
    metadata: Optional[str] = None,
):
    """Upload artifact to entry."""
    try:
        ws = Workspace.load(get_workspace_path(workspace_path))
        session = ws.db_manager.get_session()
        try:
            entry = Entry.get_by_id(session, entry_id)
            if not entry:
                raise HTTPException(status_code=404, detail="Entry not found")

            core_entry = _entry_to_core(ws, entry)

            data = await file.read()
            artifact_metadata = json.loads(metadata) if metadata else {}

            artifact = core_entry.add_artifact(
                artifact_type=file.content_type or "application/octet-stream",
                data=data,
                metadata=artifact_metadata,
            )

            return artifact
        finally:
            session.close()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{artifact_hash}")
async def get_artifact(
    artifact_hash: str,
    workspace_path: Optional[str] = Query(None),
    thumbnail: bool = Query(default=False),
):
    """Retrieve artifact by hash."""
    try:
        ws = Workspace.load(get_workspace_path(workspace_path))

        if thumbnail:
            data = ws.storage_manager.get_thumbnail(artifact_hash)
            if not data:
                raise HTTPException(status_code=404, detail="Thumbnail not found")
            media_type = "image/jpeg"
        else:
            data = ws.storage_manager.retrieve(artifact_hash)
            if not data:
                raise HTTPException(status_code=404, detail="Artifact not found")

            session = ws.db_manager.get_session()
            try:
                artifact = Artifact.find_one_by(session, hash=artifact_hash)
                media_type = artifact.type if artifact else "application/octet-stream"
            finally:
                session.close()

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
    workspace_path: Optional[str] = Query(None),
):
    """Get artifact metadata."""
    try:
        ws = Workspace.load(get_workspace_path(workspace_path))
        session = ws.db_manager.get_session()
        try:
            artifact = Artifact.find_one_by(session, hash=artifact_hash)
            if not artifact:
                raise HTTPException(status_code=404, detail="Artifact not found")

            return {
                "id": artifact.id,
                "entry_id": artifact.entry_id,
                "type": artifact.type,
                "hash": artifact.hash,
                "size_bytes": artifact.size_bytes,
                "path": artifact.path,
                "thumbnail_path": artifact.thumbnail_path,
                "created_at": (
                    artifact.created_at.isoformat() if artifact.created_at else None
                ),
                "archived": artifact.archived,
                "archive_strategy": artifact.archive_strategy,
                "original_size_bytes": artifact.original_size_bytes,
                "metadata": (
                    json.loads(artifact.metadata_) if artifact.metadata_ else {}
                ),
            }
        finally:
            session.close()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
