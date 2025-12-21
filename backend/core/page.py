"""Page operations for Lab Notebook."""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import yaml

from core.utils import slugify
from db.models import Notebook as NotebookModel
from db.models import Page as PageModel

if TYPE_CHECKING:
    from core.notebook import Notebook
    from core.workspace import Workspace


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

        # Create user-facing markdown file (not a directory)
        date_str = page.date.strftime("%Y-%m-%d") if page.date else "undated"
        page_slug = slugify(title)
        page_file = notebook.get_directory() / f"{date_str}-{page_slug}.md"
        
        # Ensure notebook directory exists
        notebook.get_directory().mkdir(parents=True, exist_ok=True)

        # Write markdown file with frontmatter and narrative sections
        page._write_markdown_file(page_file)

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

    def get_directory(self) -> Path:
        """Get the user-facing directory for this page.
        
        Note: This method is deprecated. Pages are now markdown files, not directories.
        Use get_file_path() instead. This is kept for backward compatibility with
        legacy page directories.
        """
        notebook = self.get_notebook()
        date_str = self.date.strftime("%Y-%m-%d") if self.date else "undated"
        page_slug = slugify(self.title)
        return notebook.get_directory() / f"{date_str}-{page_slug}"

    def get_file_path(self) -> Path:
        """Get the markdown file path for this page."""
        notebook = self.get_notebook()
        date_str = self.date.strftime("%Y-%m-%d") if self.date else "undated"
        page_slug = slugify(self.title)
        return notebook.get_directory() / f"{date_str}-{page_slug}.md"

    def _write_sidecar(self, page_dir: Optional[Path] = None) -> None:
        """Write a sidecar properties file for this page.
        
        Note: This method is deprecated in favor of frontmatter in markdown files.
        Kept for backward compatibility.
        """
        if page_dir is None:
            page_dir = self.get_directory()

        # The sidecar file is named .{directory_name}.json
        sidecar_path = page_dir.parent / f".{page_dir.name}.json"

        sidecar_data = {
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
            "type": "page",
        }

        with open(sidecar_path, "w") as f:
            json.dump(sidecar_data, f, indent=2)

    def _write_markdown_file(self, file_path: Optional[Path] = None) -> None:
        """Write page as a markdown file with frontmatter and narrative sections."""
        if file_path is None:
            file_path = self.get_file_path()

        # Build frontmatter with page metadata
        frontmatter = {
            "id": self.id,
            "notebook_id": self.notebook_id,
            "title": self.title,
            "type": "page",
        }
        
        if self.date:
            frontmatter["date"] = (
                self.date.isoformat() if isinstance(self.date, datetime) else self.date
            )
        
        frontmatter["created_at"] = (
            self.created_at.isoformat()
            if isinstance(self.created_at, datetime)
            else self.created_at
        )
        frontmatter["updated_at"] = (
            self.updated_at.isoformat()
            if isinstance(self.updated_at, datetime)
            else self.updated_at
        )
        
        if self.tags:
            frontmatter["tags"] = self.tags
        
        if self.metadata:
            frontmatter["metadata"] = self.metadata

        # Build markdown content with narrative sections
        content_parts = []
        
        # Goals section
        if self.narrative.get("goals"):
            content_parts.append("## Goals\n")
            content_parts.append(f"{self.narrative['goals']}\n")
        else:
            content_parts.append("## Goals\n\n")
        
        # Hypothesis section
        if self.narrative.get("hypothesis"):
            content_parts.append("## Hypothesis\n")
            content_parts.append(f"{self.narrative['hypothesis']}\n")
        else:
            content_parts.append("## Hypothesis\n\n")
        
        # Observations section
        if self.narrative.get("observations"):
            content_parts.append("## Observations\n")
            content_parts.append(f"{self.narrative['observations']}\n")
        else:
            content_parts.append("## Observations\n\n")
        
        # Conclusions section
        if self.narrative.get("conclusions"):
            content_parts.append("## Conclusions\n")
            content_parts.append(f"{self.narrative['conclusions']}\n")
        else:
            content_parts.append("## Conclusions\n\n")
        
        # Next Steps section
        if self.narrative.get("next_steps"):
            content_parts.append("## Next Steps\n")
            content_parts.append(f"{self.narrative['next_steps']}\n")
        else:
            content_parts.append("## Next Steps\n\n")

        # Write the markdown file with frontmatter
        with open(file_path, "w") as f:
            # Write frontmatter
            f.write("---\n")
            import yaml
            f.write(yaml.dump(frontmatter, default_flow_style=False, sort_keys=False))
            f.write("---\n\n")
            
            # Write content
            f.write("".join(content_parts))

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

        # Update markdown file
        self._write_markdown_file()

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

        # Update markdown file
        self._write_markdown_file()

        return self

    def delete(self) -> bool:
        """Delete this page."""
        # Delete markdown file if exists
        try:
            file_path = self.get_file_path()
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass  # Ignore errors when deleting file

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
        from core.notebook import Notebook

        session = self.workspace.db_manager.get_session()
        try:
            notebook = NotebookModel.get_by_id(session, self.notebook_id)
            if notebook:
                return Notebook.from_dict(
                    self.workspace,
                    {
                        "id": notebook.id,
                        "title": notebook.title,
                        "description": notebook.description,
                        "created_at": (
                            notebook.created_at.isoformat()
                            if notebook.created_at
                            else None
                        ),
                        "updated_at": (
                            notebook.updated_at.isoformat()
                            if notebook.updated_at
                            else None
                        ),
                        "settings": (
                            json.loads(notebook.settings) if notebook.settings else {}
                        ),
                        "metadata": (
                            json.loads(notebook.metadata_) if notebook.metadata_ else {}
                        ),
                        "tags": (
                            [nt.tag.name for nt in notebook.tags]
                            if notebook.tags
                            else []
                        ),
                    },
                )
            raise ValueError(f"Notebook {self.notebook_id} not found")
        finally:
            session.close()
