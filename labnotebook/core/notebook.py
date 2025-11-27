"""Notebook operations for Lab Notebook."""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from labnotebook.core.utils import slugify

if TYPE_CHECKING:
    from labnotebook.core.page import Page
    from labnotebook.core.workspace import Workspace


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

        # Create in database
        workspace.db_manager.insert_notebook(notebook.to_dict())

        # Create Git structure
        workspace.git_manager.create_notebook(notebook_id, notebook.to_dict())

        # Create user-facing directory
        notebook_dir = workspace.notebooks_path / slugify(title)
        notebook_dir.mkdir(exist_ok=True)

        # Create README
        with open(notebook_dir / "README.md", "w") as f:
            f.write(f"# {title}\n\n{description}\n\nCreated: {notebook.created_at.isoformat()}\n")

        return notebook

    @classmethod
    def from_dict(cls, workspace: "Workspace", data: dict) -> "Notebook":
        """Create a notebook from a dictionary."""
        return cls(
            id=data["id"],
            workspace=workspace,
            title=data["title"],
            description=data.get("description", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"],
            updated_at=datetime.fromisoformat(data["updated_at"]) if isinstance(data["updated_at"], str) else data["updated_at"],
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
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            "tags": self.tags,
            "settings": self.settings,
            "metadata": self.metadata,
        }

    def create_page(
        self,
        title: str,
        date: Optional[datetime] = None,
        narrative: Optional[dict] = None,
    ) -> "Page":
        """Create a new page in this notebook."""
        from labnotebook.core.page import Page

        return Page.create(self, title, date, narrative or {})

    def list_pages(self) -> list["Page"]:
        """List all pages in this notebook."""
        from labnotebook.core.page import Page

        pages_data = self.workspace.db_manager.list_pages(self.id)
        return [Page.from_dict(self.workspace, p_data) for p_data in pages_data]

    def get_page(self, page_id: str) -> Optional["Page"]:
        """Get a page by ID."""
        from labnotebook.core.page import Page

        page_data = self.workspace.db_manager.get_page(page_id)
        if page_data:
            return Page.from_dict(self.workspace, page_data)
        return None

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

        # Update in database
        self.workspace.db_manager.update_notebook(self.id, self.to_dict())

        # Update in Git
        self.workspace.git_manager.update_notebook(self.id, self.to_dict())

        return self

    def delete(self) -> bool:
        """Delete this notebook."""
        # Delete from database
        result = self.workspace.db_manager.delete_notebook(self.id)

        # Delete from Git
        self.workspace.git_manager.delete_notebook(self.id)

        return result

    def get_directory(self) -> Path:
        """Get the user-facing directory for this notebook."""
        return self.workspace.notebooks_path / slugify(self.title)
