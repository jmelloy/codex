"""File routes."""

from fastapi import APIRouter, Depends
from backend.db.models import User
from backend.api.auth import get_current_active_user


router = APIRouter()


@router.get("/")
async def list_files(
    notebook_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """List all files in a notebook."""
    # TODO: Implement file listing
    return {"message": "List files", "notebook_id": notebook_id}


@router.get("/{file_id}")
async def get_file(
    file_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific file."""
    # TODO: Implement file retrieval
    return {"message": "Get file", "file_id": file_id}


@router.post("/")
async def create_file(
    notebook_id: int,
    path: str,
    content: str,
    current_user: User = Depends(get_current_active_user)
):
    """Create a new file."""
    # TODO: Implement file creation
    return {"message": "Create file", "path": path}


@router.put("/{file_id}")
async def update_file(
    file_id: int,
    content: str,
    current_user: User = Depends(get_current_active_user)
):
    """Update a file."""
    # TODO: Implement file update
    return {"message": "Update file", "file_id": file_id}
