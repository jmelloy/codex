"""Entry operations for Lab Notebook."""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from ulid import ULID

from codex.db.models import Artifact as ArtifactModel
from codex.db.models import Entry as EntryModel
from codex.db.models import EntryLineage as EntryLineageModel
from codex.db.models import Page as PageModel

if TYPE_CHECKING:
    from codex.core.page import Page
    from codex.core.workspace import Workspace


def _now() -> datetime:
    """Get current time without timezone info for SQLite compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class Entry:
    """An individual experiment/observation entry."""

    id: str
    page_id: str
    workspace: "Workspace"
    entry_type: str
    title: str
    created_at: datetime
    status: str

    parent_id: Optional[str] = None
    inputs: dict = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)
    execution: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        page: "Page",
        entry_type: str,
        title: str,
        inputs: dict,
        parent_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> "Entry":
        """Create a new entry."""
        entry_id = str(ULID())

        entry = cls(
            id=entry_id,
            page_id=page.id,
            workspace=page.workspace,
            entry_type=entry_type,
            title=title,
            created_at=_now(),
            status="created",
            parent_id=parent_id,
            inputs=inputs,
            outputs={},
            execution={},
            metrics={},
            metadata={
                "tags": tags or [],
                "notes": "",
                "rating": None,
                "archived": False,
            },
            tags=tags or [],
        )

        # Save to database
        session = page.workspace.db_manager.get_session()
        try:
            EntryModel.create(
                session,
                validate_fk=True,
                id=entry_id,
                page_id=page.id,
                entry_type=entry_type,
                title=title,
                created_at=_now(),
                status="created",
                parent_id=parent_id,
                inputs=json.dumps(inputs),
                outputs=json.dumps({}),
                execution=json.dumps({}),
                metrics=json.dumps({}),
                metadata_=json.dumps({
                    "tags": tags or [],
                    "notes": "",
                    "rating": None,
                    "archived": False,
                }),
            )

            # Update lineage if has parent
            if parent_id:
                EntryLineageModel.create(
                    session,
                    validate_fk=True,
                    parent_id=parent_id,
                    child_id=entry_id,
                    relationship_type="derives_from",
                    created_at=_now(),
                )

            session.commit()
        finally:
            session.close()

        # Get notebook_id from page
        notebook_id = page.notebook_id

        # Commit manifest to Git
        page.workspace.git_manager.commit_entry(
            notebook_id, page.id, entry_id, entry.to_dict()
        )

        return entry

    @classmethod
    def from_dict(cls, workspace: "Workspace", data: dict) -> "Entry":
        """Create an entry from a dictionary."""
        return cls(
            id=data["id"],
            page_id=data["page_id"],
            workspace=workspace,
            entry_type=data["entry_type"],
            title=data["title"],
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if isinstance(data["created_at"], str)
                else data["created_at"]
            ),
            status=data["status"],
            parent_id=data.get("parent_id"),
            inputs=data.get("inputs", {}),
            outputs=data.get("outputs", {}),
            execution=data.get("execution", {}),
            metrics=data.get("metrics", {}),
            metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
        )

    def to_dict(self) -> dict:
        """Convert entry to dictionary."""
        return {
            "id": self.id,
            "page_id": self.page_id,
            "entry_type": self.entry_type,
            "title": self.title,
            "created_at": (
                self.created_at.isoformat()
                if isinstance(self.created_at, datetime)
                else self.created_at
            ),
            "status": self.status,
            "parent_id": self.parent_id,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "execution": self.execution,
            "metrics": self.metrics,
            "metadata": self.metadata,
            "tags": self.tags,
        }

    async def execute(self, integration_class=None):
        """Execute this entry using its integration."""
        from codex.integrations.registry import IntegrationRegistry

        self.status = "running"
        self.execution["started_at"] = _now().isoformat()
        self._update()

        try:
            # Get integration
            if integration_class is None:
                integration_class = IntegrationRegistry.get(self.entry_type)

            integration = integration_class(self.workspace)

            # Execute
            result = await integration.execute(self.inputs)

            # Store outputs
            self.outputs = result.get("outputs", {})
            self.execution["completed_at"] = _now().isoformat()
            self.execution["status"] = "success"
            self.status = "completed"

            # Store artifacts
            if "artifacts" in result:
                for artifact_data in result["artifacts"]:
                    self.add_artifact(
                        artifact_type=artifact_data["type"],
                        data=artifact_data["data"],
                        metadata=artifact_data.get("metadata", {}),
                    )
        except Exception as e:
            self.execution["completed_at"] = _now().isoformat()
            self.execution["status"] = "error"
            self.execution["error"] = str(e)
            self.status = "failed"
            raise
        finally:
            self._update()

    def _update(self):
        """Update entry in database and Git."""
        session = self.workspace.db_manager.get_session()
        try:
            entry = EntryModel.get_by_id(session, self.id)
            if entry:
                entry.update(
                    session,
                    validate_fk=False,
                    title=self.title,
                    status=self.status,
                    outputs=json.dumps(self.outputs),
                    execution=json.dumps(self.execution),
                    metrics=json.dumps(self.metrics),
                    metadata_=json.dumps(self.metadata),
                )
                session.commit()
        finally:
            session.close()

        # Get page to get notebook_id
        session = self.workspace.db_manager.get_session()
        try:
            page = PageModel.get_by_id(session, self.page_id)
            if page:
                self.workspace.git_manager.update_entry(
                    page.notebook_id, self.page_id, self.id, self.to_dict()
                )
        finally:
            session.close()

    def add_artifact(
        self,
        artifact_type: str,
        data: bytes,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Add artifact to this entry."""
        # Store in content-addressable storage
        artifact_hash = self.workspace.storage_manager.store(data, artifact_type)

        artifact_id = f"art-{hashlib.sha256(artifact_hash.encode()).hexdigest()[:12]}"

        artifact_data = {
            "id": artifact_id,
            "entry_id": self.id,
            "type": artifact_type,
            "hash": artifact_hash,
            "size_bytes": len(data),
            "path": str(self.workspace.storage_manager.get_blob_path(artifact_hash)),
            "thumbnail_path": str(
                self.workspace.storage_manager.get_thumbnail_path(artifact_hash)
            ),
            "metadata": metadata or {},
        }

        self.workspace.db_manager.insert_artifact(artifact_data)

        return artifact_data

    def get_artifacts(self) -> list[dict]:
        """Get all artifacts for this entry."""
        session = self.workspace.db_manager.get_session()
        try:
            artifacts = ArtifactModel.find_by(session, entry_id=self.id)
            return [
                {
                    "id": a.id,
                    "entry_id": a.entry_id,
                    "type": a.type,
                    "hash": a.hash,
                    "size_bytes": a.size_bytes,
                    "path": a.path,
                    "thumbnail_path": a.thumbnail_path,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                    "archived": a.archived,
                    "archive_strategy": a.archive_strategy,
                    "original_size_bytes": a.original_size_bytes,
                    "metadata": json.loads(a.metadata_) if a.metadata_ else {},
                }
                for a in artifacts
            ]
        finally:
            session.close()

    def get_lineage(self, depth: int = 3) -> dict:
        """Get lineage graph for this entry."""
        # Get ancestors
        session = self.workspace.db_manager.get_session()
        try:
            ancestors = []
            current_ids = [self.id]

            for _ in range(depth):
                if not current_ids:
                    break

                lineages = []
                for cid in current_ids:
                    lineages.extend(EntryLineageModel.find_by(session, child_id=cid))

                parent_ids = [lineage.parent_id for lineage in lineages]
                if parent_ids:
                    entries = []
                    for pid in parent_ids:
                        e = EntryModel.get_by_id(session, pid)
                        if e:
                            entries.append({
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
                    ancestors.extend(entries)
                    current_ids = parent_ids
                else:
                    break

            # Get descendants
            descendants = []
            current_ids = [self.id]

            for _ in range(depth):
                if not current_ids:
                    break

                lineages = []
                for cid in current_ids:
                    lineages.extend(EntryLineageModel.find_by(session, parent_id=cid))

                child_ids = [lineage.child_id for lineage in lineages]
                if child_ids:
                    entries = []
                    for cid in child_ids:
                        e = EntryModel.get_by_id(session, cid)
                        if e:
                            entries.append({
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
                    descendants.extend(entries)
                    current_ids = child_ids
                else:
                    break
        finally:
            session.close()

        return {
            "ancestors": ancestors,
            "descendants": descendants,
            "entry": self.to_dict(),
        }

    def create_variation(
        self,
        title: str,
        input_overrides: dict,
        tags: Optional[list[str]] = None,
    ) -> "Entry":
        """Create a variation of this entry."""
        from codex.core.page import Page

        # Merge inputs with overrides
        new_inputs = {**self.inputs}
        for key, value in input_overrides.items():
            if (
                isinstance(value, dict)
                and key in new_inputs
                and isinstance(new_inputs[key], dict)
            ):
                new_inputs[key] = {**new_inputs[key], **value}
            else:
                new_inputs[key] = value

        # Get parent page
        session = self.workspace.db_manager.get_session()
        try:
            page_model = PageModel.get_by_id(session, self.page_id)
            page_data = {
                "id": page_model.id,
                "notebook_id": page_model.notebook_id,
                "title": page_model.title,
                "date": page_model.date.isoformat() if page_model.date else None,
                "created_at": page_model.created_at.isoformat() if page_model.created_at else None,
                "updated_at": page_model.updated_at.isoformat() if page_model.updated_at else None,
                "narrative": json.loads(page_model.narrative) if page_model.narrative else {},
                "tags": [pt.tag.name for pt in page_model.tags] if page_model.tags else [],
                "metadata": json.loads(page_model.metadata_) if page_model.metadata_ else {},
            }
        finally:
            session.close()

        page = Page.from_dict(self.workspace, page_data)

        # Create variation without parent_id to avoid duplicate lineage entry
        variation = Entry.create(
            page=page,
            entry_type=self.entry_type,
            title=title,
            inputs=new_inputs,
            parent_id=None,  # Don't set parent_id, we'll add variation_of relationship instead
            tags=tags or self.tags,
        )

        # Store parent_id in the variation object
        variation.parent_id = self.id
        variation._update()

        # Add variation relationship
        session = self.workspace.db_manager.get_session()
        try:
            EntryLineageModel.create(
                session,
                validate_fk=True,
                parent_id=self.id,
                child_id=variation.id,
                relationship_type="variation_of",
                created_at=_now(),
            )
            session.commit()
        finally:
            session.close()

        return variation

    def update(self, **kwargs) -> "Entry":
        """Update entry properties."""
        if "title" in kwargs:
            self.title = kwargs["title"]
        if "status" in kwargs:
            self.status = kwargs["status"]
        if "outputs" in kwargs:
            self.outputs = kwargs["outputs"]
        if "execution" in kwargs:
            self.execution = kwargs["execution"]
        if "metrics" in kwargs:
            self.metrics = kwargs["metrics"]
        if "metadata" in kwargs:
            self.metadata = kwargs["metadata"]
        if "tags" in kwargs:
            self.tags = kwargs["tags"]

        self._update()
        return self

    def delete(self) -> bool:
        """Delete this entry."""
        # Get page to get notebook_id
        session = self.workspace.db_manager.get_session()
        try:
            page = PageModel.get_by_id(session, self.page_id)
            notebook_id = page.notebook_id if page else None

            # Delete from database
            result = EntryModel.delete_by_id(session, self.id)
            session.commit()
        finally:
            session.close()

        # Delete from Git
        if notebook_id:
            self.workspace.git_manager.delete_entry(notebook_id, self.page_id, self.id)

        return result

    def get_page(self) -> "Page":
        """Get the parent page."""
        from codex.core.page import Page

        session = self.workspace.db_manager.get_session()
        try:
            page = PageModel.get_by_id(session, self.page_id)
            if page:
                return Page.from_dict(self.workspace, {
                    "id": page.id,
                    "notebook_id": page.notebook_id,
                    "title": page.title,
                    "date": page.date.isoformat() if page.date else None,
                    "created_at": page.created_at.isoformat() if page.created_at else None,
                    "updated_at": page.updated_at.isoformat() if page.updated_at else None,
                    "narrative": json.loads(page.narrative) if page.narrative else {},
                    "tags": [pt.tag.name for pt in page.tags] if page.tags else [],
                    "metadata": json.loads(page.metadata_) if page.metadata_ else {},
                })
            raise ValueError(f"Page {self.page_id} not found")
        finally:
            session.close()
