"""Page operations for Lab Notebook."""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from labnotebook.core.utils import slugify

if TYPE_CHECKING:
    from labnotebook.core.entry import Entry
    from labnotebook.core.notebook import Notebook
    from labnotebook.core.workspace import Workspace


def _now() -> datetime:
    """Get current time without timezone info for SQLite compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class Page:
    """A page contains entries and narrative."""

    id: str
    notebook_id: str
    workspace: "Workspace"
    title: str
    date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    narrative: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        notebook: "Notebook",
        title: str,
        date: Optional[datetime] = None,
        narrative: Optional[dict] = None,
    ) -> "Page":
        """Create a new page."""
        page_id = f"page-{hashlib.sha256(f'{_now().isoformat()}-{title}'.encode()).hexdigest()[:12]}"

        now = _now()
        page = cls(
            id=page_id,
            notebook_id=notebook.id,
            workspace=notebook.workspace,
            title=title,
            date=date or now,
            created_at=now,
            updated_at=now,
            narrative=narrative or {
                "goals": "",
                "hypothesis": "",
                "observations": "",
                "conclusions": "",
                "next_steps": "",
            },
            tags=[],
            metadata={},
        )

        # Save to database
        notebook.workspace.db_manager.insert_page(page.to_dict())

        # Commit to Git
        notebook.workspace.git_manager.create_page(notebook.id, page_id, page.to_dict())

        # Create user-facing directory
        date_str = page.date.strftime("%Y-%m-%d") if page.date else "undated"
        page_slug = slugify(title)
        page_dir = notebook.get_directory() / f"{date_str}-{page_slug}"
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "entries").mkdir(exist_ok=True)

        # Create README with narrative
        with open(page_dir / "README.md", "w") as f:
            f.write(f"# {title}\n\n")
            f.write(f"**Date**: {date_str}\n\n")
            f.write(f"## Goals\n{page.narrative.get('goals', '')}\n\n")
            f.write(f"## Hypothesis\n{page.narrative.get('hypothesis', '')}\n\n")
            f.write("## Observations\n\n")
            f.write("## Conclusions\n\n")
            f.write("## Next Steps\n\n")

        return page

    @classmethod
    def from_dict(cls, workspace: "Workspace", data: dict) -> "Page":
        """Create a page from a dictionary."""
        return cls(
            id=data["id"],
            notebook_id=data["notebook_id"],
            workspace=workspace,
            title=data["title"],
            date=datetime.fromisoformat(data["date"]) if data.get("date") and isinstance(data["date"], str) else data.get("date"),
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"],
            updated_at=datetime.fromisoformat(data["updated_at"]) if isinstance(data["updated_at"], str) else data["updated_at"],
            narrative=data.get("narrative", {}),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )

    def to_dict(self) -> dict:
        """Convert page to dictionary."""
        return {
            "id": self.id,
            "notebook_id": self.notebook_id,
            "title": self.title,
            "date": self.date.isoformat() if isinstance(self.date, datetime) else self.date,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            "narrative": self.narrative,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    def create_entry(
        self,
        entry_type: str,
        title: str,
        inputs: dict,
        parent_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> "Entry":
        """Create a new entry on this page."""
        from labnotebook.core.entry import Entry

        return Entry.create(
            self,
            entry_type,
            title,
            inputs,
            parent_id,
            tags or [],
        )

    def list_entries(self) -> list["Entry"]:
        """List all entries on this page."""
        from labnotebook.core.entry import Entry

        entries_data = self.workspace.db_manager.list_entries(self.id)
        return [Entry.from_dict(self.workspace, e_data) for e_data in entries_data]

    def get_entry(self, entry_id: str) -> Optional["Entry"]:
        """Get an entry by ID."""
        from labnotebook.core.entry import Entry

        entry_data = self.workspace.db_manager.get_entry(entry_id)
        if entry_data:
            return Entry.from_dict(self.workspace, entry_data)
        return None

    def update_narrative(self, field_name: str, content: str):
        """Update narrative field."""
        self.narrative[field_name] = content
        self.updated_at = _now()
        self.workspace.db_manager.update_page(self.id, {"narrative": self.narrative})
        self.workspace.git_manager.update_page(self.notebook_id, self.id, self.to_dict())

    def update(self, **kwargs) -> "Page":
        """Update page properties."""
        if "title" in kwargs:
            self.title = kwargs["title"]
        if "date" in kwargs:
            self.date = kwargs["date"]
        if "narrative" in kwargs:
            self.narrative = kwargs["narrative"]
        if "tags" in kwargs:
            self.tags = kwargs["tags"]
        if "metadata" in kwargs:
            self.metadata = kwargs["metadata"]

        self.updated_at = _now()

        # Update in database
        self.workspace.db_manager.update_page(self.id, self.to_dict())

        # Update in Git
        self.workspace.git_manager.update_page(self.notebook_id, self.id, self.to_dict())

        return self

    def delete(self) -> bool:
        """Delete this page."""
        # Delete from database
        result = self.workspace.db_manager.delete_page(self.id)

        # Delete from Git
        self.workspace.git_manager.delete_page(self.notebook_id, self.id)

        return result

    def get_notebook(self) -> "Notebook":
        """Get the parent notebook."""
        from labnotebook.core.notebook import Notebook

        notebook_data = self.workspace.db_manager.get_notebook(self.notebook_id)
        if notebook_data:
            return Notebook.from_dict(self.workspace, notebook_data)
        raise ValueError(f"Notebook {self.notebook_id} not found")
