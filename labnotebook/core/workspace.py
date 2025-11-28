"""Workspace management for Lab Notebook."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from labnotebook.core.git_manager import GitManager
from labnotebook.core.storage import StorageManager
from labnotebook.db.operations import DatabaseManager

if TYPE_CHECKING:
    from labnotebook.core.notebook import Notebook


def _now() -> datetime:
    """Get current time without timezone info for SQLite compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Workspace:
    """Root workspace containing notebooks."""

    def __init__(self, path: Path):
        """Initialize a workspace instance."""
        self.path = Path(path).resolve()
        self.lab_path = self.path / ".lab"
        self.notebooks_path = self.path / "notebooks"
        self.artifacts_path = self.path / "artifacts"

        # Managers
        self._db_manager: Optional[DatabaseManager] = None
        self._storage_manager: Optional[StorageManager] = None
        self._git_manager: Optional[GitManager] = None

    @property
    def db_manager(self) -> DatabaseManager:
        """Get the database manager."""
        if self._db_manager is None:
            self._db_manager = DatabaseManager(self.lab_path / "db" / "index.db")
        return self._db_manager

    @property
    def storage_manager(self) -> StorageManager:
        """Get the storage manager."""
        if self._storage_manager is None:
            self._storage_manager = StorageManager(self.lab_path / "storage")
        return self._storage_manager

    @property
    def git_manager(self) -> GitManager:
        """Get the Git manager."""
        if self._git_manager is None:
            self._git_manager = GitManager(self.lab_path / "git")
            self._git_manager.load()
        return self._git_manager

    @classmethod
    def initialize(cls, path: Path, name: str) -> "Workspace":
        """Initialize a new workspace."""
        ws = cls(path)

        # Create directory structure
        ws.lab_path.mkdir(parents=True, exist_ok=True)
        (ws.lab_path / "db").mkdir(exist_ok=True)
        (ws.lab_path / "storage" / "blobs").mkdir(parents=True, exist_ok=True)
        (ws.lab_path / "storage" / "thumbnails").mkdir(parents=True, exist_ok=True)
        ws.notebooks_path.mkdir(parents=True, exist_ok=True)
        ws.artifacts_path.mkdir(parents=True, exist_ok=True)

        # Initialize Git
        ws._git_manager = GitManager.initialize(ws.lab_path / "git")

        # Initialize database
        ws._db_manager = DatabaseManager(ws.lab_path / "db" / "index.db")
        ws._db_manager.initialize()

        # Initialize storage
        ws._storage_manager = StorageManager(ws.lab_path / "storage")
        ws._storage_manager.initialize()

        # Create config
        config = {
            "name": name,
            "version": "1.0.0",
            "created_at": _now().isoformat(),
        }

        with open(ws.lab_path / "config.json", "w") as f:
            json.dump(config, f, indent=2)

        return ws

    @classmethod
    def load(cls, path: Path) -> "Workspace":
        """Load an existing workspace."""
        ws = cls(path)

        if not ws.is_initialized():
            raise ValueError(f"No workspace found at {path}")

        return ws

    def is_initialized(self) -> bool:
        """Check if workspace is initialized."""
        return (self.lab_path / "config.json").exists()

    def get_config(self) -> dict:
        """Get workspace configuration."""
        config_path = self.lab_path / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                return json.load(f)
        return {}

    def create_notebook(
        self,
        title: str,
        description: str = "",
        tags: Optional[list[str]] = None,
    ) -> "Notebook":
        """Create a new notebook."""
        from labnotebook.core.notebook import Notebook

        return Notebook.create(self, title, description, tags or [])

    def list_notebooks(self) -> list["Notebook"]:
        """List all notebooks."""
        from labnotebook.core.notebook import Notebook

        notebooks_data = self.db_manager.list_notebooks()
        return [Notebook.from_dict(self, nb_data) for nb_data in notebooks_data]

    def get_notebook(self, notebook_id: str) -> Optional["Notebook"]:
        """Get a notebook by ID."""
        from labnotebook.core.notebook import Notebook

        notebook_data = self.db_manager.get_notebook(notebook_id)
        if notebook_data:
            return Notebook.from_dict(self, notebook_data)
        return None

    def search_entries(
        self,
        query: Optional[str] = None,
        entry_type: Optional[str] = None,
        tags: Optional[list[str]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        notebook_id: Optional[str] = None,
        page_id: Optional[str] = None,
    ) -> list[dict]:
        """Search entries across the workspace."""
        filters = {
            "query": query,
            "entry_type": entry_type,
            "tags": tags,
            "date_from": date_from,
            "date_to": date_to,
            "notebook_id": notebook_id,
            "page_id": page_id,
        }
        return self.db_manager.search_entries(filters)
