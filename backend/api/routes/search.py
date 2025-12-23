"""Search routes."""

from fastapi import APIRouter, Depends
from backend.db.models import User
from backend.api.auth import get_current_active_user


router = APIRouter()


@router.get("/")
async def search(
    q: str,
    workspace_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Search files and content in a workspace."""
    # TODO: Implement full-text search
    return {"message": "Search", "query": q, "workspace_id": workspace_id}


@router.get("/tags")
async def search_by_tags(
    tags: str,
    workspace_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Search files by tags."""
    # TODO: Implement tag search
    tag_list = tags.split(",")
    return {"message": "Search by tags", "tags": tag_list, "workspace_id": workspace_id}
