"""Page operations for Lab Notebook."""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from codex.core.utils import slugify
from codex.db.models import Entry as EntryModel
from codex.db.models import Notebook as NotebookModel
from codex.db.models import Page as PageModel

if TYPE_CHECKING:
    from codex.core.entry import Entry
    from codex.core.notebook import Notebook
    from codex.core.workspace import Workspace


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
            narrative=narrative
            or {
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
        session = notebook.workspace.db_manager.get_session()
        try:
            PageModel.create(
                session,
                validate_fk=True,
                id=page_id,
                notebook_id=notebook.id,
                title=title,
                date=date or now,
                created_at=now,
                updated_at=now,
                narrative=json.dumps(page.narrative),
                metadata_=json.dumps(page.metadata),
            )
            session.commit()
        finally:
            session.close()

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
            date=(
                datetime.fromisoformat(data["date"])
                if data.get("date") and isinstance(data["date"], str)
                else data.get("date")
            ),
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
            "date": (
                self.date.isoformat() if isinstance(self.date, datetime) else self.date
            ),
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
        from codex.core.entry import Entry

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
        from codex.core.entry import Entry

        session = self.workspace.db_manager.get_session()
        try:
            entries = EntryModel.find_by(session, page_id=self.id)
            return [
                Entry.from_dict(self.workspace, {
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
                })
                for e in entries
            ]
        finally:
            session.close()

    def get_entry(self, entry_id: str) -> Optional["Entry"]:
        """Get an entry by ID."""
        from codex.core.entry import Entry

        session = self.workspace.db_manager.get_session()
        try:
            entry = EntryModel.get_by_id(session, entry_id)
            if entry:
                return Entry.from_dict(self.workspace, {
                    "id": entry.id,
                    "page_id": entry.page_id,
                    "entry_type": entry.entry_type,
                    "title": entry.title,
                    "created_at": entry.created_at.isoformat() if entry.created_at else None,
                    "status": entry.status,
                    "parent_id": entry.parent_id,
                    "inputs": json.loads(entry.inputs) if entry.inputs else {},
                    "outputs": json.loads(entry.outputs) if entry.outputs else {},
                    "execution": json.loads(entry.execution) if entry.execution else {},
                    "metrics": json.loads(entry.metrics) if entry.metrics else {},
                    "metadata": json.loads(entry.metadata_) if entry.metadata_ else {},
                    "tags": [et.tag.name for et in entry.tags] if entry.tags else [],
                })
            return None
        finally:
            session.close()

    def update_narrative(self, field_name: str, content: str):
        """Update narrative field."""
        self.narrative[field_name] = content
        self.updated_at = _now()

        session = self.workspace.db_manager.get_session()
        try:
            page = PageModel.get_by_id(session, self.id)
            if page:
                page.update(
                    session,
                    validate_fk=False,
                    narrative=json.dumps(self.narrative),
                    updated_at=self.updated_at,
                )
                session.commit()
        finally:
            session.close()

        self.workspace.git_manager.update_page(
            self.notebook_id, self.id, self.to_dict()
        )

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
        session = self.workspace.db_manager.get_session()
        try:
            page = PageModel.get_by_id(session, self.id)
            if page:
                page.update(
                    session,
                    validate_fk=False,
                    title=self.title,
                    date=self.date,
                    updated_at=self.updated_at,
                    narrative=json.dumps(self.narrative),
                    metadata_=json.dumps(self.metadata),
                )
                session.commit()
        finally:
            session.close()

        # Update in Git
        self.workspace.git_manager.update_page(
            self.notebook_id, self.id, self.to_dict()
        )

        return self

    def delete(self) -> bool:
        """Delete this page."""
        # Delete from database
        session = self.workspace.db_manager.get_session()
        try:
            result = PageModel.delete_by_id(session, self.id)
            session.commit()
        finally:
            session.close()

        # Delete from Git
        self.workspace.git_manager.delete_page(self.notebook_id, self.id)

        return result

    def get_notebook(self) -> "Notebook":
        """Get the parent notebook."""
        from codex.core.notebook import Notebook

        session = self.workspace.db_manager.get_session()
        try:
            notebook = NotebookModel.get_by_id(session, self.notebook_id)
            if notebook:
                return Notebook.from_dict(self.workspace, {
                    "id": notebook.id,
                    "title": notebook.title,
                    "description": notebook.description,
                    "created_at": notebook.created_at.isoformat() if notebook.created_at else None,
                    "updated_at": notebook.updated_at.isoformat() if notebook.updated_at else None,
                    "settings": json.loads(notebook.settings) if notebook.settings else {},
                    "metadata": json.loads(notebook.metadata_) if notebook.metadata_ else {},
                    "tags": [nt.tag.name for nt in notebook.tags] if notebook.tags else [],
                })
            raise ValueError(f"Notebook {self.notebook_id} not found")
        finally:
            session.close()
