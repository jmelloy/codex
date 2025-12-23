"""Notebook database operations for per-notebook data."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from db.notebook_models import (
    MarkdownFile,
    Page,
    PageTag,
    Tag,
    get_notebook_engine,
    get_notebook_session,
    init_notebook_db,
)


def _now() -> datetime:
    """Get current time without timezone info for SQLite compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _parse_datetime(value) -> datetime:
    """Parse a datetime value, handling both strings and datetime objects."""
    if value is None:
        return _now()
    if isinstance(value, str):
        # Remove timezone info if present for SQLite compatibility
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.replace(tzinfo=None)
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    return _now()


class NotebookDatabaseManager:
    """Manager for per-notebook database operations."""

    def __init__(self, db_path: Path, notebook_id: str):
        """Initialize the notebook database manager.
        
        Args:
            db_path: Path to the notebook database file
            notebook_id: ID of the notebook this database belongs to
        """
        self.db_path = db_path
        self.notebook_id = notebook_id
        self.engine = None
        self._session = None

    def initialize(self):
        """Initialize the notebook database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = init_notebook_db(str(self.db_path))

    def get_session(self) -> Session:
        """Get a database session."""
        if self.engine is None:
            self.engine = get_notebook_engine(str(self.db_path))
        return get_notebook_session(self.engine)

    # Page operations
    def create_page(self, page_data: dict) -> Page:
        """Create a new page."""
        session = self.get_session()
        try:
            page = Page.create(
                session,
                id=page_data["id"],
                notebook_id=self.notebook_id,
                title=page_data["title"],
                date=(
                    _parse_datetime(page_data.get("date"))
                    if page_data.get("date")
                    else None
                ),
                created_at=_parse_datetime(page_data.get("created_at")),
                updated_at=_parse_datetime(page_data.get("updated_at")),
                narrative=json.dumps(page_data.get("narrative", {})),
                metadata_=json.dumps(page_data.get("metadata", {})),
            )

            # Handle tags
            for tag_name in page_data.get("tags", []):
                tag = self._get_or_create_tag(session, tag_name)
                PageTag.create(session, page_id=page.id, tag_id=tag.id)

            session.commit()
            return page
        finally:
            session.close()

    def get_page(self, page_id: str) -> Optional[Page]:
        """Get a page by ID."""
        session = self.get_session()
        try:
            return Page.get_by_id(session, page_id)
        finally:
            session.close()

    def list_pages(self) -> list[Page]:
        """List all pages in this notebook."""
        session = self.get_session()
        try:
            return Page.find_by(session, notebook_id=self.notebook_id)
        finally:
            session.close()

    def update_page(self, page_id: str, data: dict) -> Optional[Page]:
        """Update a page."""
        session = self.get_session()
        try:
            page = Page.get_by_id(session, page_id)
            if page:
                update_data = {"updated_at": _now()}
                if "title" in data:
                    update_data["title"] = data["title"]
                if "date" in data:
                    update_data["date"] = _parse_datetime(data["date"]) if data["date"] else None
                if "narrative" in data:
                    update_data["narrative"] = json.dumps(data["narrative"])
                if "metadata" in data:
                    update_data["metadata_"] = json.dumps(data["metadata"])
                
                page.update(session, **update_data)
                session.commit()
                return page
            return None
        finally:
            session.close()

    def delete_page(self, page_id: str) -> bool:
        """Delete a page."""
        session = self.get_session()
        try:
            return Page.delete_by_id(session, page_id)
        finally:
            session.close()

    # Tag operations
    def _get_or_create_tag(self, session: Session, tag_name: str) -> Tag:
        """Get or create a tag."""
        tag = Tag.find_one_by(session, name=tag_name)
        if not tag:
            tag = Tag.create(session, name=tag_name)
            session.flush()
        return tag

    def list_tags(self) -> list[Tag]:
        """List all tags in this notebook."""
        session = self.get_session()
        try:
            return Tag.get_all(session)
        finally:
            session.close()

    # Markdown file indexing operations
    def index_markdown_file(self, file_data: dict) -> MarkdownFile:
        """Index a markdown file."""
        session = self.get_session()
        try:
            # Check if file already exists
            existing = MarkdownFile.find_one_by(session, relative_path=file_data["relative_path"])
            if existing:
                # Update existing entry
                existing.update(
                    session,
                    path=file_data["path"],
                    title=file_data.get("title"),
                    file_hash=file_data["file_hash"],
                    frontmatter=file_data.get("frontmatter"),
                    file_size=file_data.get("file_size"),
                    file_modified=file_data.get("file_modified"),
                    indexed_at=_now(),
                    updated_at=_now(),
                )
                session.commit()
                return existing
            else:
                # Create new entry
                markdown_file = MarkdownFile.create(
                    session,
                    path=file_data["path"],
                    relative_path=file_data["relative_path"],
                    title=file_data.get("title"),
                    file_hash=file_data["file_hash"],
                    frontmatter=file_data.get("frontmatter"),
                    file_size=file_data.get("file_size"),
                    file_modified=file_data.get("file_modified"),
                    indexed_at=_now(),
                    created_at=_now(),
                    updated_at=_now(),
                )
                session.commit()
                return markdown_file
        finally:
            session.close()

    def search_markdown_files(self, query: Optional[str] = None, limit: int = 100) -> list[MarkdownFile]:
        """Search markdown files in this notebook."""
        session = self.get_session()
        try:
            query_obj = session.query(MarkdownFile)
            
            if query:
                # Simple title search - can be enhanced with FTS later
                query_obj = query_obj.filter(MarkdownFile.title.like(f"%{query}%"))
            
            query_obj = query_obj.limit(limit)
            return query_obj.all()
        finally:
            session.close()

    def remove_stale_markdown_entries(self, existing_paths: set[str]) -> int:
        """Remove markdown file entries that no longer exist on disk."""
        session = self.get_session()
        try:
            all_files = MarkdownFile.get_all(session)
            removed_count = 0
            
            for md_file in all_files:
                if md_file.relative_path not in existing_paths:
                    md_file.delete(session)
                    removed_count += 1
            
            if removed_count > 0:
                session.commit()
            
            return removed_count
        finally:
            session.close()
