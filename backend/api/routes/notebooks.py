"""Notebook routes."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.api.auth import get_current_active_user
from backend.db.database import get_notebook_session, get_system_session, init_notebook_db
from backend.db.models import Notebook, User, Workspace

router = APIRouter()


@router.get("/")
async def list_notebooks(
    workspace_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session)
):
    """List all notebooks in a workspace."""
    # Verify workspace access
    result = await session.execute(
        select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.owner_id == current_user.id
        )
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Notebooks are stored in per-notebook databases within the workspace directory
    # We need to scan the workspace directory for notebook directories
    workspace_path = Path(workspace.path)
    if not workspace_path.exists():
        return []

    notebooks = []
    # Look for directories with .codex subdirectories (indicating notebooks)
    for item in workspace_path.iterdir():
        if item.is_dir():
            codex_dir = item / ".codex"
            if codex_dir.exists():
                # This is a notebook directory
                notebook_db_path = codex_dir / "notebook.db"
                if notebook_db_path.exists():
                    # Query the notebook database for metadata
                    try:
                        nb_session = get_notebook_session(str(item))
                        result = nb_session.execute(select(Notebook))
                        notebook_records = result.scalars().all()
                        for nb in notebook_records:
                            notebooks.append({
                                "id": nb.id,
                                "name": nb.name,
                                "path": nb.path,
                                "description": nb.description,
                                "created_at": nb.created_at.isoformat() if nb.created_at else None,
                                "updated_at": nb.updated_at.isoformat() if nb.updated_at else None
                            })
                        nb_session.close()
                    except Exception as e:
                        print(f"Error reading notebook {item}: {e}")

    return notebooks


@router.get("/{notebook_id}")
async def get_notebook(
    notebook_id: int,
    workspace_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session)
):
    """Get a specific notebook."""
    # Verify workspace access
    result = await session.execute(
        select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.owner_id == current_user.id
        )
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Scan workspace for notebook
    workspace_path = Path(workspace.path)
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail="Notebook not found")

    for item in workspace_path.iterdir():
        if item.is_dir():
            codex_dir = item / ".codex"
            notebook_db_path = codex_dir / "notebook.db"
            if notebook_db_path.exists():
                try:
                    nb_session = get_notebook_session(str(item))
                    result = nb_session.execute(
                        select(Notebook).where(Notebook.id == notebook_id)
                    )
                    notebook = result.scalar_one_or_none()
                    nb_session.close()

                    if notebook:
                        return {
                            "id": notebook.id,
                            "name": notebook.name,
                            "path": notebook.path,
                            "description": notebook.description,
                            "created_at": notebook.created_at.isoformat() if notebook.created_at else None,
                            "updated_at": notebook.updated_at.isoformat() if notebook.updated_at else None
                        }
                except Exception as e:
                    print(f"Error reading notebook {item}: {e}")

    raise HTTPException(status_code=404, detail="Notebook not found")


@router.post("/")
async def create_notebook(
    workspace_id: int,
    name: str,
    path: str,
    description: str = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session)
):
    """Create a new notebook."""
    # Verify workspace access
    result = await session.execute(
        select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.owner_id == current_user.id
        )
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Create notebook directory
    workspace_path = Path(workspace.path)
    notebook_path = workspace_path / path

    if notebook_path.exists():
        raise HTTPException(status_code=400, detail="Notebook path already exists")

    try:
        notebook_path.mkdir(parents=True, exist_ok=False)

        # Initialize notebook database
        init_notebook_db(str(notebook_path))

        # Create notebook record in the database
        nb_session = get_notebook_session(str(notebook_path))
        notebook = Notebook(
            name=name,
            path=path,
            description=description
        )
        nb_session.add(notebook)
        nb_session.commit()
        nb_session.refresh(notebook)

        result = {
            "id": notebook.id,
            "name": notebook.name,
            "path": notebook.path,
            "description": notebook.description,
            "created_at": notebook.created_at.isoformat() if notebook.created_at else None,
            "updated_at": notebook.updated_at.isoformat() if notebook.updated_at else None
        }

        nb_session.close()
        return result

    except Exception as e:
        # Clean up on error
        if notebook_path.exists():
            import shutil
            shutil.rmtree(notebook_path)
        raise HTTPException(status_code=500, detail=f"Error creating notebook: {str(e)}")
