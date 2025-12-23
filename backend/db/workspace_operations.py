"""Workspace database operations for notebook registry."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from db.workspace_models import (
    Notebook,
    get_workspace_engine,
    get_workspace_session,
    init_workspace_db,
)


def _now() -> datetime:
    """Get current time without timezone info for SQLite compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class WorkspaceDatabaseManager:
    """Manager for workspace database operations (notebook registry)."""

    def __init__(self, db_path: Path):
        """Initialize the workspace database manager.
        
        Args:
            db_path: Path to the workspace database file
        """
        self.db_path = db_path
        self.engine = None
        self._session = None

    def initialize(self):
        """Initialize the workspace database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = init_workspace_db(str(self.db_path))

    def get_session(self) -> Session:
        """Get a database session."""
        if self.engine is None:
            self.engine = get_workspace_engine(str(self.db_path))
        return get_workspace_session(self.engine)

    # Notebook registry operations
    def register_notebook(
        self,
        notebook_id: str,
        title: str,
        description: str,
        db_path: str,
        settings: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> Notebook:
        """Register a new notebook in the workspace."""
        session = self.get_session()
        try:
            notebook = Notebook.create(
                session,
                id=notebook_id,
                title=title,
                description=description,
                db_path=db_path,
                settings=json.dumps(settings or {}),
                metadata_=json.dumps(metadata or {}),
                created_at=_now(),
                updated_at=_now(),
            )
            session.commit()
            return notebook
        finally:
            session.close()

    def get_notebook(self, notebook_id: str) -> Optional[Notebook]:
        """Get a notebook by ID."""
        session = self.get_session()
        try:
            return Notebook.get_by_id(session, notebook_id)
        finally:
            session.close()

    def list_notebooks(self) -> list[Notebook]:
        """List all notebooks in the workspace."""
        session = self.get_session()
        try:
            return Notebook.get_all(session)
        finally:
            session.close()

    def update_notebook(
        self,
        notebook_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        settings: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[Notebook]:
        """Update a notebook."""
        session = self.get_session()
        try:
            notebook = Notebook.get_by_id(session, notebook_id)
            if notebook:
                update_data = {"updated_at": _now()}
                if title is not None:
                    update_data["title"] = title
                if description is not None:
                    update_data["description"] = description
                if settings is not None:
                    update_data["settings"] = json.dumps(settings)
                if metadata is not None:
                    update_data["metadata_"] = json.dumps(metadata)
                
                notebook.update(session, **update_data)
                session.commit()
                return notebook
            return None
        finally:
            session.close()

    def delete_notebook(self, notebook_id: str) -> bool:
        """Delete a notebook from the registry."""
        session = self.get_session()
        try:
            return Notebook.delete_by_id(session, notebook_id)
        finally:
            session.close()
