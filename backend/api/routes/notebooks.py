"""Notebook routes."""

from fastapi import APIRouter, Depends, HTTPException
from typing import List

from backend.db.models import User
from backend.api.auth import get_current_active_user


router = APIRouter()


@router.get("/")
async def list_notebooks(
    workspace_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """List all notebooks in a workspace."""
    # TODO: Implement notebook listing from workspace database
    return {"message": "List notebooks", "workspace_id": workspace_id}


@router.get("/{notebook_id}")
async def get_notebook(
    notebook_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific notebook."""
    # TODO: Implement notebook retrieval
    return {"message": "Get notebook", "notebook_id": notebook_id}


@router.post("/")
async def create_notebook(
    workspace_id: int,
    name: str,
    path: str,
    current_user: User = Depends(get_current_active_user)
):
    """Create a new notebook."""
    # TODO: Implement notebook creation
    return {"message": "Create notebook", "name": name, "path": path}
