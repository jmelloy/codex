"""Markdown-based storage for notebooks, pages, and entries.

This module provides a simplified storage approach using markdown files
as the primary data store instead of SQLite database tables.
"""

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

from core.markdown import MarkdownDocument
from core.utils import slugify


def _now() -> datetime:
    """Get current time without timezone info for consistency."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class MarkdownNotebook:
    """Notebook stored as a directory with markdown files."""

    def __init__(self, path: Path):
        """Initialize notebook from a directory path.
        
        Args:
            path: Path to notebook directory (contains index.md)
        """
        self.path = Path(path).resolve()
        self.index_file = self.path / "index.md"
        
        # Load notebook data from index.md
        if self.index_file.exists():
            self._load()
        else:
            self.id = ""
            self.title = ""
            self.description = ""
            self.created_at = _now()
            self.updated_at = _now()
            self.tags = []
            self.settings = {}
            self.metadata = {}

    def _load(self):
        """Load notebook data from index.md."""
        doc = MarkdownDocument.parse(self.index_file.read_text(encoding="utf-8"))
        
        # Extract properties from frontmatter
        self.id = doc.frontmatter.get("id", "")
        self.title = doc.frontmatter.get("title", "")
        self.description = doc.frontmatter.get("description", "")
        self.created_at = self._parse_datetime(doc.frontmatter.get("created_at"))
        self.updated_at = self._parse_datetime(doc.frontmatter.get("updated_at"))
        self.tags = doc.frontmatter.get("tags", [])
        self.settings = doc.frontmatter.get("settings", {})
        self.metadata = doc.frontmatter.get("metadata", {})

    def _parse_datetime(self, value: Any) -> datetime:
        """Parse datetime from various formats."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return _now()

    def save(self):
        """Save notebook data to index.md."""
        # Ensure directory exists
        self.path.mkdir(parents=True, exist_ok=True)
        
        # Build frontmatter
        frontmatter = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags,
            "settings": self.settings,
            "metadata": self.metadata,
        }
        
        # Build content
        content = f"# {self.title}\n\n{self.description}\n\n## Pages\n\n"
        
        # List pages
        pages = self.list_pages()
        for page_file in pages:
            page_name = page_file.stem
            content += f"- [{page_name}]({page_file.name})\n"
        
        # Create document
        doc = MarkdownDocument(frontmatter=frontmatter, content=content)
        
        # Write to file
        self.index_file.write_text(doc.to_markdown(), encoding="utf-8")

    @classmethod
    def create(
        cls,
        workspace_path: Path,
        title: str,
        description: str = "",
        tags: Optional[list[str]] = None,
    ) -> "MarkdownNotebook":
        """Create a new notebook.
        
        Args:
            workspace_path: Path to workspace
            title: Notebook title
            description: Notebook description
            tags: List of tags
            
        Returns:
            New MarkdownNotebook instance
        """
        # Generate ID
        notebook_id = f"nb-{hashlib.sha256(f'{_now().isoformat()}-{title}'.encode()).hexdigest()[:12]}"
        
        # Create notebook directory
        slug = slugify(title)
        notebook_path = workspace_path / "notebooks" / slug
        notebook_path.mkdir(parents=True, exist_ok=True)
        
        # Create notebook instance
        notebook = cls(notebook_path)
        notebook.id = notebook_id
        notebook.title = title
        notebook.description = description
        notebook.created_at = _now()
        notebook.updated_at = _now()
        notebook.tags = tags or []
        notebook.settings = {
            "default_entry_type": "custom",
            "auto_archive_days": 90,
            "archive_strategy": "compress",
        }
        notebook.metadata = {}
        
        # Save
        notebook.save()
        
        return notebook

    def list_pages(self) -> list[Path]:
        """List all page files in this notebook.
        
        Returns:
            List of page markdown file paths
        """
        if not self.path.exists():
            return []
        
        # Find all markdown files except index.md
        pages = []
        for file in self.path.glob("*.md"):
            if file.name != "index.md":
                pages.append(file)
        
        # Sort by filename (which includes date prefix)
        pages.sort()
        return pages

    def create_page(
        self,
        title: str,
        date: Optional[datetime] = None,
        narrative: Optional[dict] = None,
    ) -> "MarkdownPage":
        """Create a new page in this notebook.
        
        Args:
            title: Page title
            date: Page date
            narrative: Narrative structure
            
        Returns:
            New MarkdownPage instance
        """
        return MarkdownPage.create(self, title, date, narrative)

    def get_page(self, page_id: str) -> Optional["MarkdownPage"]:
        """Get a page by ID.
        
        Args:
            page_id: Page ID
            
        Returns:
            MarkdownPage instance or None
        """
        for page_file in self.list_pages():
            page = MarkdownPage(page_file)
            if page.id == page_id:
                return page
        return None

    def to_dict(self) -> dict:
        """Convert notebook to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags,
            "settings": self.settings,
            "metadata": self.metadata,
        }


class MarkdownPage:
    """Page stored as a markdown file."""

    def __init__(self, path: Path):
        """Initialize page from a file path.
        
        Args:
            path: Path to page markdown file
        """
        self.path = Path(path).resolve()
        
        # Load page data from markdown file
        if self.path.exists():
            self._load()
        else:
            self.id = ""
            self.notebook_id = ""
            self.title = ""
            self.date = _now()
            self.created_at = _now()
            self.updated_at = _now()
            self.narrative = {}
            self.tags = []
            self.metadata = {}
            self.entries = []

    def _load(self):
        """Load page data from markdown file."""
        doc = MarkdownDocument.parse(self.path.read_text(encoding="utf-8"))
        
        # Extract properties from frontmatter
        self.id = doc.frontmatter.get("id", "")
        self.notebook_id = doc.frontmatter.get("notebook_id", "")
        self.title = doc.frontmatter.get("title", "")
        self.date = self._parse_datetime(doc.frontmatter.get("date"))
        self.created_at = self._parse_datetime(doc.frontmatter.get("created_at"))
        self.updated_at = self._parse_datetime(doc.frontmatter.get("updated_at"))
        self.narrative = doc.frontmatter.get("narrative", {})
        self.tags = doc.frontmatter.get("tags", [])
        self.metadata = doc.frontmatter.get("metadata", {})
        self.entries = doc.frontmatter.get("entries", [])

    def _parse_datetime(self, value: Any) -> datetime:
        """Parse datetime from various formats."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return _now()

    def save(self):
        """Save page data to markdown file."""
        # Build frontmatter
        frontmatter = {
            "id": self.id,
            "notebook_id": self.notebook_id,
            "title": self.title,
            "date": self.date.isoformat() if self.date else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "narrative": self.narrative,
            "tags": self.tags,
            "metadata": self.metadata,
            "entries": self.entries,
        }
        
        # Build content with narrative sections
        content_parts = [f"# {self.title}\n"]
        
        if self.narrative.get("goals"):
            content_parts.append(f"## Goals\n\n{self.narrative['goals']}\n")
        
        if self.narrative.get("hypothesis"):
            content_parts.append(f"## Hypothesis\n\n{self.narrative['hypothesis']}\n")
        
        if self.narrative.get("observations"):
            content_parts.append(f"## Observations\n\n{self.narrative['observations']}\n")
        
        if self.narrative.get("conclusions"):
            content_parts.append(f"## Conclusions\n\n{self.narrative['conclusions']}\n")
        
        if self.narrative.get("next_steps"):
            content_parts.append(f"## Next Steps\n\n{self.narrative['next_steps']}\n")
        
        # Add entries section
        if self.entries:
            content_parts.append("## Entries\n")
            for entry in self.entries:
                content_parts.append(f"\n### {entry.get('title', 'Untitled')}\n")
                content_parts.append(f"\n**Type**: {entry.get('entry_type', 'unknown')}\n")
                content_parts.append(f"**Created**: {entry.get('created_at', '')}\n")
                content_parts.append(f"**Status**: {entry.get('status', 'unknown')}\n")
                
                if entry.get("inputs"):
                    content_parts.append("\n**Inputs**:\n```json\n")
                    content_parts.append(json.dumps(entry["inputs"], indent=2))
                    content_parts.append("\n```\n")
                
                if entry.get("outputs"):
                    content_parts.append("\n**Outputs**:\n```json\n")
                    content_parts.append(json.dumps(entry["outputs"], indent=2))
                    content_parts.append("\n```\n")
                
                if entry.get("artifacts"):
                    content_parts.append("\n**Artifacts**:\n")
                    for artifact in entry["artifacts"]:
                        artifact_path = artifact.get("path", "")
                        artifact_type = artifact.get("type", "")
                        if artifact_type.startswith("image/"):
                            content_parts.append(f"![Artifact]({artifact_path})\n")
                        else:
                            content_parts.append(f"- [{artifact_path}]({artifact_path})\n")
        
        content = "\n".join(content_parts)
        
        # Create document
        doc = MarkdownDocument(frontmatter=frontmatter, content=content)
        
        # Write to file
        self.path.write_text(doc.to_markdown(), encoding="utf-8")

    @classmethod
    def create(
        cls,
        notebook: MarkdownNotebook,
        title: str,
        date: Optional[datetime] = None,
        narrative: Optional[dict] = None,
    ) -> "MarkdownPage":
        """Create a new page.
        
        Args:
            notebook: Parent notebook
            title: Page title
            date: Page date
            narrative: Narrative structure
            
        Returns:
            New MarkdownPage instance
        """
        # Generate ID
        page_id = f"page-{hashlib.sha256(f'{_now().isoformat()}-{title}'.encode()).hexdigest()[:12]}"
        
        # Create page file path
        date_obj = date or _now()
        date_str = date_obj.strftime("%Y-%m-%d")
        slug = slugify(title)
        page_path = notebook.path / f"{date_str}-{slug}.md"
        
        # Create page instance
        page = cls(page_path)
        page.id = page_id
        page.notebook_id = notebook.id
        page.title = title
        page.date = date_obj
        page.created_at = _now()
        page.updated_at = _now()
        page.narrative = narrative or {
            "goals": "",
            "hypothesis": "",
            "observations": "",
            "conclusions": "",
            "next_steps": "",
        }
        page.tags = []
        page.metadata = {}
        page.entries = []
        
        # Save
        page.save()
        
        # Update notebook index
        notebook.updated_at = _now()
        notebook.save()
        
        return page

    def add_entry(self, entry_data: dict):
        """Add an entry to this page.
        
        Args:
            entry_data: Entry data dictionary
        """
        self.entries.append(entry_data)
        self.updated_at = _now()
        self.save()

    def update_narrative(self, field: str, content: str):
        """Update a narrative field.
        
        Args:
            field: Narrative field name
            content: Field content
        """
        self.narrative[field] = content
        self.updated_at = _now()
        self.save()

    def to_dict(self) -> dict:
        """Convert page to dictionary."""
        return {
            "id": self.id,
            "notebook_id": self.notebook_id,
            "title": self.title,
            "date": self.date.isoformat() if self.date else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "narrative": self.narrative,
            "tags": self.tags,
            "metadata": self.metadata,
            "entries": self.entries,
        }


class MarkdownWorkspace:
    """Workspace that uses markdown files for storage."""

    def __init__(self, path: Path):
        """Initialize workspace.
        
        Args:
            path: Path to workspace root
        """
        self.path = Path(path).resolve()
        self.notebooks_path = self.path / "notebooks"
        self.artifacts_path = self.path / "artifacts"
        self.config_file = self.path / "config.yaml"

    @classmethod
    def initialize(cls, path: Path, name: str) -> "MarkdownWorkspace":
        """Initialize a new workspace.
        
        Args:
            path: Path to workspace root
            name: Workspace name
            
        Returns:
            New MarkdownWorkspace instance
        """
        ws = cls(path)
        
        # Create directories
        ws.notebooks_path.mkdir(parents=True, exist_ok=True)
        ws.artifacts_path.mkdir(parents=True, exist_ok=True)
        
        # Create config
        config = {
            "name": name,
            "version": "1.0.0",
            "created_at": _now().isoformat(),
            "storage_type": "markdown",
        }
        
        with open(ws.config_file, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        
        return ws

    def list_notebooks(self) -> list[MarkdownNotebook]:
        """List all notebooks in workspace.
        
        Returns:
            List of MarkdownNotebook instances
        """
        notebooks = []
        if self.notebooks_path.exists():
            for notebook_dir in self.notebooks_path.iterdir():
                if notebook_dir.is_dir() and (notebook_dir / "index.md").exists():
                    notebooks.append(MarkdownNotebook(notebook_dir))
        return notebooks

    def get_notebook(self, notebook_id: str) -> Optional[MarkdownNotebook]:
        """Get a notebook by ID.
        
        Args:
            notebook_id: Notebook ID
            
        Returns:
            MarkdownNotebook instance or None
        """
        for notebook in self.list_notebooks():
            if notebook.id == notebook_id:
                return notebook
        return None

    def create_notebook(
        self,
        title: str,
        description: str = "",
        tags: Optional[list[str]] = None,
    ) -> MarkdownNotebook:
        """Create a new notebook.
        
        Args:
            title: Notebook title
            description: Notebook description
            tags: List of tags
            
        Returns:
            New MarkdownNotebook instance
        """
        return MarkdownNotebook.create(self.path, title, description, tags)
