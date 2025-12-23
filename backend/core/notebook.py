"""Notebook operations for Lab Notebook."""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from core.utils import slugify
from db.models import Notebook as NotebookModel
from db.models import Page as PageModel

if TYPE_CHECKING:
    from core.page import Page
    from core.workspace import Workspace


def _now() -> datetime:
    """Get current time without timezone info for SQLite compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class Notebook:
    """A notebook contains pages."""

    id: str
    workspace: "Workspace"
    title: str
    description: str
    created_at: datetime
    updated_at: datetime
    tags: list[str] = field(default_factory=list)
    settings: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    _notebook_repo = None  # Git repo for this notebook

    @classmethod
    def create(
        cls,
        workspace: "Workspace",
        title: str,
        description: str = "",
        tags: Optional[list[str]] = None,
    ) -> "Notebook":
        """Create a new notebook."""
        notebook_id = f"nb-{hashlib.sha256(f'{_now().isoformat()}-{title}'.encode()).hexdigest()[:12]}"

        now = _now()
        notebook = cls(
            id=notebook_id,
            workspace=workspace,
            title=title,
            description=description,
            created_at=now,
            updated_at=now,
            tags=tags or [],
            settings={
                "default_entry_type": "custom",
                "auto_archive_days": 90,
                "archive_strategy": "compress",
            },
            metadata={},
        )

        # Create notebook directory
        notebook_dir = workspace.notebooks_path / notebook_id
        notebook_dir.mkdir(exist_ok=True)
        
        # Create notebook's .lab directory for its database
        notebook_lab_dir = notebook_dir / ".lab"
        notebook_lab_dir.mkdir(exist_ok=True)
        
        # Path to notebook's database
        notebook_db_path = notebook_lab_dir / "notebook.db"

        # Register in workspace database (notebook registry)
        workspace.workspace_db_manager.register_notebook(
            notebook_id=notebook_id,
            title=title,
            description=description,
            db_path=str(notebook_db_path),
            settings=notebook.settings,
            metadata=notebook.metadata,
        )

        # Initialize notebook's own database
        notebook_db_manager = workspace.get_notebook_db_manager(notebook_id)
        notebook_db_manager.initialize()

        # Create Git structure
        workspace.git_manager.create_notebook(notebook_id, notebook.to_dict())

        # Create user-facing directory
        user_notebook_dir = workspace.notebooks_path / slugify(title)
        user_notebook_dir.mkdir(exist_ok=True)

        # Create README
        readme_path = user_notebook_dir / "README.md"
        with open(readme_path, "w") as f:
            f.write(
                f"# {title}\n\n{description}\n\nCreated: {notebook.created_at.isoformat()}\n"
            )

        # Write sidecar properties file
        notebook._write_sidecar()

        # Initialize notebook git repository
        notebook._init_notebook_git()

        return notebook

    @classmethod
    def from_dict(cls, workspace: "Workspace", data: dict) -> "Notebook":
        """Create a notebook from a dictionary."""
        return cls(
            id=data["id"],
            workspace=workspace,
            title=data["title"],
            description=data.get("description", ""),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if isinstance(data["created_at"], str)
                else data["created_at"]
            ),
            updated_at=(
                datetime.fromisoformat(data["updated_at"])
                if isinstance(data["updated_at"], str)
                else data["updated_at"]
            ),
            tags=data.get("tags", []),
            settings=data.get("settings", {}),
            metadata=data.get("metadata", {}),
        )

    def to_dict(self) -> dict:
        """Convert notebook to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "created_at": (
                self.created_at.isoformat()
                if isinstance(self.created_at, datetime)
                else self.created_at
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if isinstance(self.updated_at, datetime)
                else self.updated_at
            ),
            "tags": self.tags,
            "settings": self.settings,
            "metadata": self.metadata,
        }

    def _write_sidecar(self) -> None:
        """Write a sidecar properties file for this notebook."""
        notebook_dir = self.get_directory()

        # The sidecar file is named .{directory_name}.json
        sidecar_path = notebook_dir.parent / f".{notebook_dir.name}.json"

        sidecar_data = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "created_at": (
                self.created_at.isoformat()
                if isinstance(self.created_at, datetime)
                else self.created_at
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if isinstance(self.updated_at, datetime)
                else self.updated_at
            ),
            "tags": self.tags,
            "settings": self.settings,
            "metadata": self.metadata,
            "type": "notebook",
        }

        with open(sidecar_path, "w") as f:
            json.dump(sidecar_data, f, indent=2)

    def _init_notebook_git(self):
        """Initialize git repository for this notebook."""
        try:
            from git import Repo
            from git.exc import InvalidGitRepositoryError
        except ImportError:
            return  # Git not available

        notebook_dir = self.get_directory()

        try:
            # Check if already a git repo
            self._notebook_repo = Repo(notebook_dir)
        except InvalidGitRepositoryError:
            # Initialize new git repo
            self._notebook_repo = Repo.init(notebook_dir)

            # Create .gitignore to exclude sidecar files
            gitignore_path = notebook_dir / ".gitignore"
            if not gitignore_path.exists():
                with open(gitignore_path, "w") as f:
                    f.write("# Sidecar metadata files\n")
                    f.write(".*.json\n")
                    f.write("\n")
                    f.write("# Python cache\n")
                    f.write("__pycache__/\n")
                    f.write("*.pyc\n")

            # Create initial commit with README and .gitignore
            self._notebook_repo.index.add([".gitignore", "README.md"])
            self._notebook_repo.index.commit(f"Initialize notebook: {self.title}")

    def _load_notebook_git(self):
        """Load existing notebook git repository."""
        try:
            from git import Repo
            from git.exc import InvalidGitRepositoryError
        except ImportError:
            return  # Git not available

        notebook_dir = self.get_directory()
        try:
            self._notebook_repo = Repo(notebook_dir)
        except InvalidGitRepositoryError:
            pass  # No git repo, that's ok

    def commit_file_changes(self, file_paths: list[Path], message: str):
        """Commit changes to files in this notebook."""
        if not self._notebook_repo:
            self._load_notebook_git()

        if not self._notebook_repo:
            return  # No git repo available

        try:
            notebook_dir = self.get_directory()
            # Convert to relative paths and add to index
            relative_paths = []
            for file_path in file_paths:
                if file_path.exists():
                    rel_path = file_path.relative_to(notebook_dir)
                    relative_paths.append(str(rel_path))

            if relative_paths:
                self._notebook_repo.index.add(relative_paths)
                self._notebook_repo.index.commit(message)
        except (OSError, IOError) as e:
            # Log but don't fail if git operations fail (e.g., permission errors)
            import logging
            logging.warning(f"Git commit failed for {file_paths}: {e}")
        except Exception as e:
            # Catch other git-related exceptions
            import logging
            logging.warning(f"Unexpected error during git commit: {e}")

    def create_page(
        self,
        title: str,
        date: Optional[datetime] = None,
        narrative: Optional[dict] = None,
    ) -> "Page":
        """Create a new page in this notebook."""
        from core.page import Page

        return Page.create(self, title, date, narrative or {})

    def list_pages(self) -> list["Page"]:
        """List all pages in this notebook."""
        from core.page import Page

        # Get pages from notebook database
        from db.notebook_models import Page as PageModel
        notebook_db = self.workspace.get_notebook_db_manager(self.id)
        session = notebook_db.get_session()
        try:
            pages = PageModel.find_by(session, notebook_id=self.id)
            return [
                Page.from_dict(
                    self.workspace,
                    {
                        "id": p.id,
                        "notebook_id": p.notebook_id,
                        "title": p.title,
                        "date": p.date.isoformat() if p.date else None,
                        "created_at": (
                            p.created_at.isoformat() if p.created_at else None
                        ),
                        "updated_at": (
                            p.updated_at.isoformat() if p.updated_at else None
                        ),
                        "narrative": json.loads(p.narrative) if p.narrative else {},
                        "tags": [pt.tag.name for pt in p.tags] if p.tags else [],
                        "metadata": json.loads(p.metadata_) if p.metadata_ else {},
                    },
                )
                for p in pages
            ]
        finally:
            session.close()

    def get_page(self, page_id: str) -> Optional["Page"]:
        """Get a page by ID."""
        from core.page import Page

        # Get page from notebook database
        from db.notebook_models import Page as PageModel
        notebook_db = self.workspace.get_notebook_db_manager(self.id)
        session = notebook_db.get_session()
        try:
            page = PageModel.get_by_id(session, page_id)
            if page:
                return Page.from_dict(
                    self.workspace,
                    {
                        "id": page.id,
                        "notebook_id": page.notebook_id,
                        "title": page.title,
                        "date": page.date.isoformat() if page.date else None,
                        "created_at": (
                            page.created_at.isoformat() if page.created_at else None
                        ),
                        "updated_at": (
                            page.updated_at.isoformat() if page.updated_at else None
                        ),
                        "narrative": (
                            json.loads(page.narrative) if page.narrative else {}
                        ),
                        "tags": [pt.tag.name for pt in page.tags] if page.tags else [],
                        "metadata": (
                            json.loads(page.metadata_) if page.metadata_ else {}
                        ),
                    },
                )
            return None
        finally:
            session.close()

    def update(self, **kwargs) -> "Notebook":
        """Update notebook properties."""
        if "title" in kwargs:
            self.title = kwargs["title"]
        if "description" in kwargs:
            self.description = kwargs["description"]
        if "tags" in kwargs:
            self.tags = kwargs["tags"]
        if "settings" in kwargs:
            self.settings = kwargs["settings"]
        if "metadata" in kwargs:
            self.metadata = kwargs["metadata"]

        self.updated_at = _now()

        # Update in workspace database
        self.workspace.workspace_db_manager.update_notebook(
            self.id,
            title=self.title,
            description=self.description,
            settings=self.settings,
            metadata=self.metadata,
        )

        # Update in Git
        self.workspace.git_manager.update_notebook(self.id, self.to_dict())

        # Update sidecar file
        self._write_sidecar()

        return self

    def delete(self) -> bool:
        """Delete this notebook."""
        # Delete sidecar file if exists
        try:
            notebook_dir = self.get_directory()
            sidecar_path = notebook_dir.parent / f".{notebook_dir.name}.json"
            if sidecar_path.exists():
                sidecar_path.unlink()
        except Exception:
            pass  # Ignore errors when deleting sidecar

        # Delete from workspace database
        result = self.workspace.workspace_db_manager.delete_notebook(self.id)

        # Delete from Git
        self.workspace.git_manager.delete_notebook(self.id)

        return result

    def get_directory(self) -> Path:
        """Get the user-facing directory for this notebook."""
        return self.workspace.notebooks_path / slugify(self.title)
