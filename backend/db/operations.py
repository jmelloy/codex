"""Database operations for Lab Notebook."""

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from db.models import (
    Artifact,
    Entry,
    EntryLineage,
    EntryTag,
    IntegrationVariable,
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

    # Entry operations
    def insert_entry(self, entry_data: dict) -> Entry:
        """Insert a new entry."""
        session = self.get_session()
        try:
            entry = Entry(
                id=entry_data["id"],
                page_id=entry_data["page_id"],
                entry_type=entry_data["entry_type"],
                title=entry_data["title"],
                created_at=_parse_datetime(entry_data.get("created_at")),
                status=entry_data.get("status", "created"),
                parent_id=entry_data.get("parent_id"),
                inputs=json.dumps(entry_data.get("inputs", {})),
                outputs=json.dumps(entry_data.get("outputs", {})),
                execution=json.dumps(entry_data.get("execution", {})),
                metrics=json.dumps(entry_data.get("metrics", {})),
                metadata_=json.dumps(entry_data.get("metadata", {})),
            )
            session.add(entry)

            # Handle tags
            for tag_name in entry_data.get("tags", []):
                tag = self._get_or_create_tag(session, tag_name)
                entry_tag = EntryTag(entry_id=entry.id, tag_id=tag.id)
                session.add(entry_tag)

            session.commit()
            return entry
        finally:
            session.close()

    def get_entry(self, entry_id: str) -> dict | None:
        """Get an entry by ID."""
        session = self.get_session()
        try:
            entry = session.query(Entry).filter(Entry.id == entry_id).first()
            if entry:
                return self._entry_to_dict(entry)
            return None
        finally:
            session.close()

    def list_entries(self, page_id: str) -> list[dict]:
        """List all entries in a page."""
        session = self.get_session()
        try:
            entries = (
                session.query(Entry)
                .filter(Entry.page_id == page_id)
                .order_by(Entry.created_at.desc())
                .all()
            )
            return [self._entry_to_dict(e) for e in entries]
        finally:
            session.close()

    def update_entry(self, entry_id: str, data: dict) -> dict | None:
        """Update an entry."""
        session = self.get_session()
        try:
            entry = session.query(Entry).filter(Entry.id == entry_id).first()
            if entry:
                if "title" in data:
                    entry.title = data["title"]
                if "status" in data:
                    entry.status = data["status"]
                if "outputs" in data:
                    entry.outputs = json.dumps(data["outputs"])
                if "execution" in data:
                    entry.execution = json.dumps(data["execution"])
                if "metrics" in data:
                    entry.metrics = json.dumps(data["metrics"])
                if "metadata" in data:
                    entry.metadata_ = json.dumps(data["metadata"])
                session.commit()
                return self._entry_to_dict(entry)
            return None
        finally:
            session.close()

    def delete_entry(self, entry_id: str) -> bool:
        """Delete an entry."""
        session = self.get_session()
        try:
            entry = session.query(Entry).filter(Entry.id == entry_id).first()
            if entry:
                session.delete(entry)
                session.commit()
                return True
            return False
        finally:
            session.close()

    # Lineage operations
    def add_lineage_edge(
        self, parent_id: str, child_id: str, relationship_type: str = "derives_from"
    ) -> EntryLineage:
        """Add a lineage edge between entries."""
        session = self.get_session()
        try:
            lineage = EntryLineage(
                parent_id=parent_id,
                child_id=child_id,
                relationship_type=relationship_type,
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            session.add(lineage)
            session.commit()
            return lineage
        finally:
            session.close()

    def get_ancestors(self, entry_id: str, depth: int = 3) -> list[dict]:
        """Get ancestors of an entry."""
        session = self.get_session()
        try:
            ancestors = []
            current_ids = [entry_id]

            for _ in range(depth):
                if not current_ids:
                    break

                lineages = (
                    session.query(EntryLineage)
                    .filter(EntryLineage.child_id.in_(current_ids))
                    .all()
                )

                parent_ids = [lineage.parent_id for lineage in lineages]
                if parent_ids:
                    entries = (
                        session.query(Entry).filter(Entry.id.in_(parent_ids)).all()
                    )
                    ancestors.extend([self._entry_to_dict(e) for e in entries])
                    current_ids = parent_ids
                else:
                    break

            return ancestors
        finally:
            session.close()

    def get_descendants(self, entry_id: str, depth: int = 3) -> list[dict]:
        """Get descendants of an entry."""
        session = self.get_session()
        try:
            descendants = []
            current_ids = [entry_id]

            for _ in range(depth):
                if not current_ids:
                    break

                lineages = (
                    session.query(EntryLineage)
                    .filter(EntryLineage.parent_id.in_(current_ids))
                    .all()
                )

                child_ids = [lineage.child_id for lineage in lineages]
                if child_ids:
                    entries = session.query(Entry).filter(Entry.id.in_(child_ids)).all()
                    descendants.extend([self._entry_to_dict(e) for e in entries])
                    current_ids = child_ids
                else:
                    break

            return descendants
        finally:
            session.close()

    # Artifact operations
    def insert_artifact(self, artifact_data: dict) -> Artifact:
        """Insert a new artifact."""
        session = self.get_session()
        try:
            artifact = Artifact(
                id=artifact_data["id"],
                entry_id=artifact_data["entry_id"],
                type=artifact_data["type"],
                hash=artifact_data["hash"],
                size_bytes=artifact_data["size_bytes"],
                path=artifact_data["path"],
                thumbnail_path=artifact_data.get("thumbnail_path"),
                created_at=_parse_datetime(artifact_data.get("created_at")),
                archived=artifact_data.get("archived", False),
                archive_strategy=artifact_data.get("archive_strategy"),
                original_size_bytes=artifact_data.get("original_size_bytes"),
                metadata_=json.dumps(artifact_data.get("metadata", {})),
            )
            session.add(artifact)
            session.commit()
            return artifact
        finally:
            session.close()

    def get_artifact(self, artifact_id: str) -> dict | None:
        """Get an artifact by ID."""
        session = self.get_session()
        try:
            artifact = (
                session.query(Artifact).filter(Artifact.id == artifact_id).first()
            )
            if artifact:
                return self._artifact_to_dict(artifact)
            return None
        finally:
            session.close()

    def get_artifact_by_hash(self, hash_value: str) -> dict | None:
        """Get an artifact by hash."""
        session = self.get_session()
        try:
            artifact = (
                session.query(Artifact).filter(Artifact.hash == hash_value).first()
            )
            if artifact:
                return self._artifact_to_dict(artifact)
            return None
        finally:
            session.close()

    def list_artifacts(self, entry_id: str) -> list[dict]:
        """List all artifacts for an entry."""
        session = self.get_session()
        try:
            artifacts = (
                session.query(Artifact)
                .filter(Artifact.entry_id == entry_id)
                .order_by(Artifact.created_at.desc())
                .all()
            )
            return [self._artifact_to_dict(a) for a in artifacts]
        finally:
            session.close()

    # Search operations
    def search_entries(self, filters: dict) -> list[dict]:
        """Search entries with filters."""
        session = self.get_session()
        try:
            query = session.query(Entry)

            if filters.get("notebook_id"):
                query = query.join(Page).filter(
                    Page.notebook_id == filters["notebook_id"]
                )

            if filters.get("page_id"):
                query = query.filter(Entry.page_id == filters["page_id"])

            if filters.get("entry_type"):
                query = query.filter(Entry.entry_type == filters["entry_type"])

            if filters.get("date_from"):
                query = query.filter(Entry.created_at >= filters["date_from"])

            if filters.get("date_to"):
                query = query.filter(Entry.created_at <= filters["date_to"])

            entries = query.order_by(Entry.created_at.desc()).all()
            return [self._entry_to_dict(e) for e in entries]
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

    def _entry_to_dict(self, entry: Entry) -> dict:
        """Convert an entry to a dictionary."""
        return {
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
        }

    def _artifact_to_dict(self, artifact: Artifact) -> dict:
        """Convert an artifact to a dictionary."""
        return {
            "id": artifact.id,
            "entry_id": artifact.entry_id,
            "type": artifact.type,
            "hash": artifact.hash,
            "size_bytes": artifact.size_bytes,
            "path": artifact.path,
            "thumbnail_path": artifact.thumbnail_path,
            "created_at": (
                artifact.created_at.isoformat() if artifact.created_at else None
            ),
            "archived": artifact.archived,
            "archive_strategy": artifact.archive_strategy,
            "original_size_bytes": artifact.original_size_bytes,
            "metadata": json.loads(artifact.metadata_) if artifact.metadata_ else {},
        }

    # Integration variable operations
    def set_integration_variable(
        self,
        integration_type: str,
        name: str,
        value: str | dict | list,
        description: str | None = None,
        is_secret: bool = False,
    ) -> dict:
        """Set an integration variable (create or update).

        Args:
            integration_type: The integration type (e.g., 'api_call', 'database_query')
            name: Variable name (e.g., 'base_url', 'connection_string')
            value: Variable value (will be JSON-encoded if not a string)
            description: Optional description of the variable
            is_secret: Whether this is sensitive data (e.g., passwords)

        Returns:
            The variable as a dictionary
        """
        session = self.get_session()
        try:
            # JSON encode the value if it's not a string
            if isinstance(value, (dict, list)):
                encoded_value = json.dumps(value)
            else:
                encoded_value = str(value)

            # Try to find existing variable
            variable = (
                session.query(IntegrationVariable)
                .filter(
                    IntegrationVariable.integration_type == integration_type,
                    IntegrationVariable.name == name,
                )
                .first()
            )

            if variable:
                # Update existing
                variable.value = encoded_value
                if description is not None:
                    variable.description = description
                variable.is_secret = is_secret
                variable.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            else:
                # Create new
                variable = IntegrationVariable(
                    integration_type=integration_type,
                    name=name,
                    value=encoded_value,
                    description=description,
                    is_secret=is_secret,
                    created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
                session.add(variable)

            session.commit()
            return self._integration_variable_to_dict(variable)
        finally:
            session.close()

    def get_integration_variable(self, integration_type: str, name: str) -> dict | None:
        """Get a specific integration variable."""
        session = self.get_session()
        try:
            variable = (
                session.query(IntegrationVariable)
                .filter(
                    IntegrationVariable.integration_type == integration_type,
                    IntegrationVariable.name == name,
                )
                .first()
            )
            if variable:
                return self._integration_variable_to_dict(variable)
            return None
        finally:
            session.close()

    def get_integration_variables(self, integration_type: str) -> dict:
        """Get all variables for an integration type as a dictionary.

        Returns a dictionary mapping variable names to their values,
        suitable for merging with entry inputs.
        """
        session = self.get_session()
        try:
            variables = (
                session.query(IntegrationVariable)
                .filter(IntegrationVariable.integration_type == integration_type)
                .all()
            )
            result = {}
            for var in variables:
                # Try to decode JSON, fall back to string
                try:
                    result[var.name] = json.loads(var.value)
                except json.JSONDecodeError:
                    result[var.name] = var.value
            return result
        finally:
            session.close()

    def list_integration_variables(
        self, integration_type: str | None = None
    ) -> list[dict]:
        """List integration variables, optionally filtered by type."""
        session = self.get_session()
        try:
            query = session.query(IntegrationVariable)
            if integration_type:
                query = query.filter(
                    IntegrationVariable.integration_type == integration_type
                )
            variables = query.order_by(
                IntegrationVariable.integration_type,
                IntegrationVariable.name,
            ).all()
            return [self._integration_variable_to_dict(v) for v in variables]
        finally:
            session.close()

    def delete_integration_variable(self, integration_type: str, name: str) -> bool:
        """Delete an integration variable."""
        session = self.get_session()
        try:
            variable = (
                session.query(IntegrationVariable)
                .filter(
                    IntegrationVariable.integration_type == integration_type,
                    IntegrationVariable.name == name,
                )
                .first()
            )
            if variable:
                session.delete(variable)
                session.commit()
                return True
            return False
        finally:
            session.close()

    def _integration_variable_to_dict(self, variable: IntegrationVariable) -> dict:
        """Convert an integration variable to a dictionary."""
        # Try to decode JSON, fall back to string
        try:
            decoded_value = json.loads(variable.value)
        except json.JSONDecodeError:
            decoded_value = variable.value

        return {
            "id": variable.id,
            "integration_type": variable.integration_type,
            "name": variable.name,
            "value": decoded_value,
            "description": variable.description,
            "is_secret": variable.is_secret,
            "created_at": (
                variable.created_at.isoformat() if variable.created_at else None
            ),
            "updated_at": (
                variable.updated_at.isoformat() if variable.updated_at else None
            ),
        }
