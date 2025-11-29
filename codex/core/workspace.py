"""Workspace management for Lab Notebook."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from codex.core.git_manager import GitManager
from codex.core.storage import StorageManager
from codex.db.models import Entry as EntryModel
from codex.db.models import Notebook as NotebookModel
from codex.db.models import Page as PageModel
from codex.db.operations import DatabaseManager

if TYPE_CHECKING:
    from codex.core.notebook import Notebook


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
        from codex.core.notebook import Notebook

        return Notebook.create(self, title, description, tags or [])

    def list_notebooks(self) -> list["Notebook"]:
        """List all notebooks."""
        from codex.core.notebook import Notebook

        session = self.db_manager.get_session()
        try:
            notebooks = NotebookModel.get_all(session)
            return [
                Notebook.from_dict(self, {
                    "id": nb.id,
                    "title": nb.title,
                    "description": nb.description,
                    "created_at": nb.created_at.isoformat() if nb.created_at else None,
                    "updated_at": nb.updated_at.isoformat() if nb.updated_at else None,
                    "settings": json.loads(nb.settings) if nb.settings else {},
                    "metadata": json.loads(nb.metadata_) if nb.metadata_ else {},
                    "tags": [nt.tag.name for nt in nb.tags] if nb.tags else [],
                })
                for nb in notebooks
            ]
        finally:
            session.close()

    def get_notebook(self, notebook_id: str) -> Optional["Notebook"]:
        """Get a notebook by ID."""
        from codex.core.notebook import Notebook

        session = self.db_manager.get_session()
        try:
            notebook = NotebookModel.get_by_id(session, notebook_id)
            if notebook:
                return Notebook.from_dict(self, {
                    "id": notebook.id,
                    "title": notebook.title,
                    "description": notebook.description,
                    "created_at": notebook.created_at.isoformat() if notebook.created_at else None,
                    "updated_at": notebook.updated_at.isoformat() if notebook.updated_at else None,
                    "settings": json.loads(notebook.settings) if notebook.settings else {},
                    "metadata": json.loads(notebook.metadata_) if notebook.metadata_ else {},
                    "tags": [nt.tag.name for nt in notebook.tags] if notebook.tags else [],
                })
            return None
        finally:
            session.close()

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
        session = self.db_manager.get_session()
        try:
            query_obj = session.query(EntryModel)

            if notebook_id:
                query_obj = query_obj.join(PageModel).filter(
                    PageModel.notebook_id == notebook_id
                )

            if page_id:
                query_obj = query_obj.filter(EntryModel.page_id == page_id)

            if entry_type:
                query_obj = query_obj.filter(EntryModel.entry_type == entry_type)

            if date_from:
                query_obj = query_obj.filter(EntryModel.created_at >= date_from)

            if date_to:
                query_obj = query_obj.filter(EntryModel.created_at <= date_to)

            entries = query_obj.order_by(EntryModel.created_at.desc()).all()
            return [
                {
                    "id": e.id,
                    "page_id": e.page_id,
                    "entry_type": e.entry_type,
                    "title": e.title,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                    "status": e.status,
                    "parent_id": e.parent_id,
                    "inputs": json.loads(e.inputs) if e.inputs else {},
                    "outputs": json.loads(e.outputs) if e.outputs else {},
                    "execution": json.loads(e.execution) if e.execution else {},
                    "metrics": json.loads(e.metrics) if e.metrics else {},
                    "metadata": json.loads(e.metadata_) if e.metadata_ else {},
                    "tags": [et.tag.name for et in e.tags] if e.tags else [],
                }
                for e in entries
            ]
        finally:
            session.close()

    def _scan_directory(self, dir_path: Path, relative_base: Path) -> list[dict]:
        """
        Recursively scan a directory and return its contents.

        Args:
            dir_path: The directory path to scan.
            relative_base: The base path to compute relative paths from.

        Returns:
            A list of dictionaries representing files and directories.
        """
        items = []

        try:
            for item in sorted(dir_path.iterdir()):
                # Skip hidden files and directories
                if item.name.startswith("."):
                    continue

                relative_path = item.relative_to(relative_base)

                if item.is_dir():
                    children = self._scan_directory(item, relative_base)
                    items.append({
                        "name": item.name,
                        "path": str(relative_path),
                        "type": "directory",
                        "children": children,
                    })
                else:
                    # Get file info
                    stat_info = item.stat()
                    items.append({
                        "name": item.name,
                        "path": str(relative_path),
                        "type": "file",
                        "size": stat_info.st_size,
                        "modified": datetime.fromtimestamp(
                            stat_info.st_mtime, tz=timezone.utc
                        ).replace(tzinfo=None).isoformat(),
                        "extension": item.suffix.lower() if item.suffix else "",
                    })
        except PermissionError:
            pass

        return items

    def scan_notebooks_directory(self) -> list[dict]:
        """
        Scan the notebooks directory for files and return a hierarchical structure.

        Returns a list of file/directory entries representing the filesystem tree
        under the notebooks directory.
        """
        if not self.notebooks_path.exists():
            return []

        return self._scan_directory(self.notebooks_path, self.notebooks_path)

    def scan_artifacts_directory(self) -> list[dict]:
        """
        Scan the artifacts directory for files and return a hierarchical structure.

        Returns a list of file/directory entries representing the filesystem tree
        under the artifacts directory.
        """
        if not self.artifacts_path.exists():
            return []

        return self._scan_directory(self.artifacts_path, self.artifacts_path)
