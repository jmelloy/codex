"""Workspace management for Lab Notebook."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from core.git_manager import GitManager
from core.markdown_indexer import (
    index_directory,
    remove_stale_entries,
    search_markdown_files,
)

from db.workspace_operations import WorkspaceDatabaseManager
from db.notebook_operations import NotebookDatabaseManager

if TYPE_CHECKING:
    from core.notebook import Notebook


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
        self._workspace_db_manager: Optional[WorkspaceDatabaseManager] = None
        self._notebook_db_managers: dict[str, NotebookDatabaseManager] = {}
        self._git_manager: Optional[GitManager] = None

    @property
    def workspace_db_manager(self) -> WorkspaceDatabaseManager:
        """Get the workspace database manager (notebook registry)."""
        if self._workspace_db_manager is None:
            self._workspace_db_manager = WorkspaceDatabaseManager(
                self.lab_path / "db" / "workspace.db"
            )
        return self._workspace_db_manager

    def get_notebook_db_manager(self, notebook_id: str) -> NotebookDatabaseManager:
        """Get the database manager for a specific notebook."""
        if notebook_id not in self._notebook_db_managers:
            # Get notebook info from registry to find its database path
            notebook_entry = self.workspace_db_manager.get_notebook(notebook_id)
            if notebook_entry:
                db_path = Path(notebook_entry.db_path)
            else:
                # Default path if not found in registry
                db_path = self.notebooks_path / notebook_id / ".lab" / "notebook.db"

            self._notebook_db_managers[notebook_id] = NotebookDatabaseManager(
                db_path, notebook_id
            )
        return self._notebook_db_managers[notebook_id]

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

        # Initialize workspace database (notebook registry)
        ws._workspace_db_manager = WorkspaceDatabaseManager(
            ws.lab_path / "db" / "workspace.db"
        )
        ws._workspace_db_manager.initialize()

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

        # Auto-index markdown files on load
        ws.index_markdown_files()

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

    def index_markdown_files(self, force: bool = False) -> dict:
        """Index all markdown files in the workspace.

        This indexes markdown files in each notebook's database separately.

        Args:
            force: If True, re-index all files even if unchanged

        Returns:
            Dictionary with indexing stats per notebook
        """
        results = {}
        notebooks = self.workspace_db_manager.list_notebooks()

        for nb_entry in notebooks:
            notebook_path = self.notebooks_path / nb_entry.id
            if not notebook_path.exists():
                continue

            notebook_db_manager = self.get_notebook_db_manager(nb_entry.id)
            session = notebook_db_manager.get_session()
            try:
                # Remove stale entries
                removed = remove_stale_entries(session, notebook_path)

                # Index notebook directory
                indexed = index_directory(
                    session, notebook_path, notebook_path, recursive=True
                )

                results[nb_entry.id] = {
                    "indexed": indexed,
                    "removed": removed,
                    "total": indexed,
                }
            finally:
                session.close()

        return results

    def search_indexed_files(
        self,
        query: Optional[str] = None,
        limit: int = 100,
        notebook_id: Optional[str] = None,
    ) -> list[dict]:
        """Search indexed markdown files.

        Args:
            query: Search query string
            limit: Maximum results to return
            notebook_id: If specified, search only in this notebook

        Returns:
            List of matching file metadata
        """
        results = []

        if notebook_id:
            # Search in specific notebook
            notebook_db_manager = self.get_notebook_db_manager(notebook_id)
            session = notebook_db_manager.get_session()
            try:
                notebook_results = search_markdown_files(session, query, limit)
                results.extend(notebook_results)
            finally:
                session.close()
        else:
            # Search across all notebooks
            notebooks = self.workspace_db_manager.list_notebooks()
            per_notebook_limit = max(1, limit // len(notebooks)) if notebooks else limit

            for nb_entry in notebooks:
                notebook_db_manager = self.get_notebook_db_manager(nb_entry.id)
                session = notebook_db_manager.get_session()
                try:
                    notebook_results = search_markdown_files(
                        session, query, per_notebook_limit
                    )
                    results.extend(notebook_results)
                    if len(results) >= limit:
                        results = results[:limit]
                        break
                finally:
                    session.close()

        return results

    def create_notebook(
        self,
        title: str,
        description: str = "",
        tags: Optional[list[str]] = None,
    ) -> "Notebook":
        """Create a new notebook."""
        from core.notebook import Notebook

        return Notebook.create(self, title, description, tags or [])

    def list_notebooks(self) -> list["Notebook"]:
        """List all notebooks."""
        from core.notebook import Notebook

        notebooks = self.workspace_db_manager.list_notebooks()
        return [
            Notebook.from_dict(
                self,
                {
                    "id": nb.id,
                    "title": nb.title,
                    "description": nb.description,
                    "created_at": (
                        nb.created_at.isoformat() if nb.created_at else None
                    ),
                    "updated_at": (
                        nb.updated_at.isoformat() if nb.updated_at else None
                    ),
                    "settings": json.loads(nb.settings) if nb.settings else {},
                    "metadata": json.loads(nb.metadata_) if nb.metadata_ else {},
                    "tags": [],  # Tags moved to notebook-specific databases
                },
            )
            for nb in notebooks
        ]

    def get_notebook(self, notebook_id: str) -> Optional["Notebook"]:
        """Get a notebook by ID."""
        from core.notebook import Notebook

        notebook_entry = self.workspace_db_manager.get_notebook(notebook_id)
        if notebook_entry:
            return Notebook.from_dict(
                self,
                {
                    "id": notebook_entry.id,
                    "title": notebook_entry.title,
                    "description": notebook_entry.description,
                    "created_at": (
                        notebook_entry.created_at.isoformat()
                        if notebook_entry.created_at
                        else None
                    ),
                    "updated_at": (
                        notebook_entry.updated_at.isoformat()
                        if notebook_entry.updated_at
                        else None
                    ),
                    "settings": (
                        json.loads(notebook_entry.settings)
                        if notebook_entry.settings
                        else {}
                    ),
                    "metadata": (
                        json.loads(notebook_entry.metadata_)
                        if notebook_entry.metadata_
                        else {}
                    ),
                    "tags": [],  # Tags moved to notebook-specific databases
                },
            )
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
        """Search entries across the workspace.

        Note: Entry system is not yet implemented. Returns empty list.
        """
        # TODO: Implement entry search across notebook databases
        return []

    def _read_sidecar(self, file_path: Path) -> Optional[dict]:
        """
        Read a sidecar properties file for a file or directory.

        The sidecar file is named .{filename}.json and contains metadata.

        Args:
            file_path: The path to the file or directory.

        Returns:
            The sidecar properties as a dictionary, or None if not found.
        """
        sidecar_path = file_path.parent / f".{file_path.name}.json"
        if sidecar_path.exists():
            try:
                with open(sidecar_path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return None

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
                # Skip hidden files and directories (including sidecar files)
                if item.name.startswith("."):
                    continue

                relative_path = item.relative_to(relative_base)

                # Check for sidecar properties file
                sidecar = self._read_sidecar(item)

                if item.is_dir():
                    children = self._scan_directory(item, relative_base)
                    entry = {
                        "name": item.name,
                        "path": str(relative_path),
                        "type": "directory",
                        "children": children,
                    }
                    if sidecar:
                        entry["properties"] = sidecar
                    items.append(entry)
                else:
                    # Get file info
                    stat_info = item.stat()
                    entry = {
                        "name": item.name,
                        "path": str(relative_path),
                        "type": "file",
                        "size": stat_info.st_size,
                        "modified": datetime.fromtimestamp(
                            stat_info.st_mtime, tz=timezone.utc
                        )
                        .replace(tzinfo=None)
                        .isoformat(),
                        "extension": item.suffix.lower() if item.suffix else "",
                    }
                    if sidecar:
                        entry["properties"] = sidecar
                    items.append(entry)
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
