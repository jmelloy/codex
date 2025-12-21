"""Database operations for Lab Notebook."""

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from db.models import (
    Notebook,
    NotebookTag,
    Page,
    PageTag,
    Tag,
    get_engine,
    get_session,
    init_db,
)


def _parse_datetime(value) -> datetime:
    """Parse a datetime value, handling both strings and datetime objects."""
    if value is None:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    if isinstance(value, str):
        # Remove timezone info if present for SQLite compatibility
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.replace(tzinfo=None)
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DatabaseManager:
    """Manager for database operations."""

    def __init__(self, db_path: Path):
        """Initialize the database manager."""
        self.db_path = db_path
        self.engine = None
        self._session = None

    def initialize(self, use_migrations: bool = True):
        """Initialize the database.

        Args:
            use_migrations: If True, use Alembic migrations. If False, use create_all().
                           Defaults to True.
        """
        self.engine = init_db(str(self.db_path), use_migrations=use_migrations)

    def get_session(self) -> Session:
        """Get a database session."""
        if self.engine is None:
            self.engine = get_engine(str(self.db_path))
        return get_session(self.engine)

    def run_migrations(self, revision: str = "head") -> None:
        """Run database migrations up to the specified revision.

        Args:
            revision: Target revision (default: "head" for latest).
        """
        from db.migrate import run_migrations

        run_migrations(str(self.db_path), revision)

    def get_migration_status(self) -> dict:
        """Get current migration status.

        Returns:
            Dictionary containing current revision, head revision,
            and whether database is up to date.
        """
        from db.migrate import (
            get_current_revision,
            get_head_revision,
            get_pending_migrations,
            is_up_to_date,
        )

        return {
            "current_revision": get_current_revision(str(self.db_path)),
            "head_revision": get_head_revision(str(self.db_path)),
            "is_up_to_date": is_up_to_date(str(self.db_path)),
            "pending_migrations": get_pending_migrations(str(self.db_path)),
        }

    def get_migration_history(self) -> list[dict]:
        """Get the history of available migrations.

        Returns:
            List of migration info dictionaries.
        """
        from db.migrate import get_migration_history

        return get_migration_history(str(self.db_path))

    # Notebook operations
    def insert_notebook(self, notebook_data: dict) -> Notebook:
        """Insert a new notebook."""
        session = self.get_session()
        try:
            notebook = Notebook(
                id=notebook_data["id"],
                title=notebook_data["title"],
                description=notebook_data.get("description", ""),
                created_at=_parse_datetime(notebook_data.get("created_at")),
                updated_at=_parse_datetime(notebook_data.get("updated_at")),
                settings=json.dumps(notebook_data.get("settings", {})),
                metadata_=json.dumps(notebook_data.get("metadata", {})),
            )
            session.add(notebook)

            # Handle tags
            for tag_name in notebook_data.get("tags", []):
                tag = self._get_or_create_tag(session, tag_name)
                notebook_tag = NotebookTag(notebook_id=notebook.id, tag_id=tag.id)
                session.add(notebook_tag)

            session.commit()
            return notebook
        finally:
            session.close()

    def get_notebook(self, notebook_id: str) -> dict | None:
        """Get a notebook by ID."""
        session = self.get_session()
        try:
            notebook = (
                session.query(Notebook).filter(Notebook.id == notebook_id).first()
            )
            if notebook:
                return self._notebook_to_dict(notebook)
            return None
        finally:
            session.close()

    def list_notebooks(self) -> list[dict]:
        """List all notebooks."""
        session = self.get_session()
        try:
            notebooks = (
                session.query(Notebook).order_by(Notebook.created_at.desc()).all()
            )
            return [self._notebook_to_dict(nb) for nb in notebooks]
        finally:
            session.close()

    def update_notebook(self, notebook_id: str, data: dict) -> dict | None:
        """Update a notebook."""
        session = self.get_session()
        try:
            notebook = (
                session.query(Notebook).filter(Notebook.id == notebook_id).first()
            )
            if notebook:
                if "title" in data:
                    notebook.title = data["title"]
                if "description" in data:
                    notebook.description = data["description"]
                if "settings" in data:
                    notebook.settings = json.dumps(data["settings"])
                if "metadata" in data:
                    notebook.metadata_ = json.dumps(data["metadata"])
                notebook.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
                session.commit()
                return self._notebook_to_dict(notebook)
            return None
        finally:
            session.close()

    def delete_notebook(self, notebook_id: str) -> bool:
        """Delete a notebook."""
        session = self.get_session()
        try:
            notebook = (
                session.query(Notebook).filter(Notebook.id == notebook_id).first()
            )
            if notebook:
                session.delete(notebook)
                session.commit()
                return True
            return False
        finally:
            session.close()

    # Page operations
    def insert_page(self, page_data: dict) -> Page:
        """Insert a new page."""
        session = self.get_session()
        try:
            page = Page(
                id=page_data["id"],
                notebook_id=page_data["notebook_id"],
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
            session.add(page)

            # Handle tags
            for tag_name in page_data.get("tags", []):
                tag = self._get_or_create_tag(session, tag_name)
                page_tag = PageTag(page_id=page.id, tag_id=tag.id)
                session.add(page_tag)

            session.commit()
            return page
        finally:
            session.close()

    def get_page(self, page_id: str) -> dict | None:
        """Get a page by ID."""
        session = self.get_session()
        try:
            page = session.query(Page).filter(Page.id == page_id).first()
            if page:
                return self._page_to_dict(page)
            return None
        finally:
            session.close()

    def list_pages(self, notebook_id: str) -> list[dict]:
        """List all pages in a notebook."""
        session = self.get_session()
        try:
            pages = (
                session.query(Page)
                .filter(Page.notebook_id == notebook_id)
                .order_by(Page.date.desc())
                .all()
            )
            return [self._page_to_dict(p) for p in pages]
        finally:
            session.close()

    def update_page(self, page_id: str, data: dict) -> dict | None:
        """Update a page."""
        session = self.get_session()
        try:
            page = session.query(Page).filter(Page.id == page_id).first()
            if page:
                if "title" in data:
                    page.title = data["title"]
                if "date" in data:
                    page.date = _parse_datetime(data["date"]) if data["date"] else None
                if "narrative" in data:
                    page.narrative = json.dumps(data["narrative"])
                if "metadata" in data:
                    page.metadata_ = json.dumps(data["metadata"])
                page.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
                session.commit()
                return self._page_to_dict(page)
            return None
        finally:
            session.close()

    def delete_page(self, page_id: str) -> bool:
        """Delete a page."""
        session = self.get_session()
        try:
            page = session.query(Page).filter(Page.id == page_id).first()
            if page:
                session.delete(page)
                session.commit()
                return True
            return False
        finally:
            session.close()


    # Helper methods
    def _get_or_create_tag(self, session: Session, tag_name: str) -> Tag:
        """Get or create a tag."""
        tag = session.query(Tag).filter(Tag.name == tag_name).first()
        if not tag:
            tag = Tag(name=tag_name)
            session.add(tag)
            session.flush()
        return tag

    def _notebook_to_dict(self, notebook: Notebook) -> dict:
        """Convert a notebook to a dictionary."""
        return {
            "id": notebook.id,
            "title": notebook.title,
            "description": notebook.description,
            "created_at": (
                notebook.created_at.isoformat() if notebook.created_at else None
            ),
            "updated_at": (
                notebook.updated_at.isoformat() if notebook.updated_at else None
            ),
            "settings": json.loads(notebook.settings) if notebook.settings else {},
            "metadata": json.loads(notebook.metadata_) if notebook.metadata_ else {},
            "tags": [nt.tag.name for nt in notebook.tags] if notebook.tags else [],
        }

    def _page_to_dict(self, page: Page) -> dict:
        """Convert a page to a dictionary."""
        return {
            "id": page.id,
            "notebook_id": page.notebook_id,
            "title": page.title,
            "date": page.date.isoformat() if page.date else None,
            "created_at": page.created_at.isoformat() if page.created_at else None,
            "updated_at": page.updated_at.isoformat() if page.updated_at else None,
            "narrative": json.loads(page.narrative) if page.narrative else {},
            "metadata": json.loads(page.metadata_) if page.metadata_ else {},
            "tags": [pt.tag.name for pt in page.tags] if page.tags else [],
        }
