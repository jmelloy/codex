"""Entry operations for Lab Notebook."""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

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
        entry_id = f"entry-{hashlib.sha256(f'{_now().isoformat()}-{title}'.encode()).hexdigest()[:12]}"

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
        page.workspace.db_manager.insert_entry(entry.to_dict())

        # Get notebook_id from page
        notebook_id = page.notebook_id

        # Commit manifest to Git
        page.workspace.git_manager.commit_entry(notebook_id, page.id, entry_id, entry.to_dict())

        # Update lineage if has parent
        if parent_id:
            page.workspace.db_manager.add_lineage_edge(parent_id, entry_id, "derives_from")

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
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"],
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
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
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
        self.workspace.db_manager.update_entry(self.id, self.to_dict())

        # Get page to get notebook_id
        page_data = self.workspace.db_manager.get_page(self.page_id)
        if page_data:
            notebook_id = page_data["notebook_id"]
            self.workspace.git_manager.update_entry(notebook_id, self.page_id, self.id, self.to_dict())

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
            "thumbnail_path": str(self.workspace.storage_manager.get_thumbnail_path(artifact_hash)),
            "metadata": metadata or {},
        }

        self.workspace.db_manager.insert_artifact(artifact_data)

        return artifact_data

    def get_artifacts(self) -> list[dict]:
        """Get all artifacts for this entry."""
        return self.workspace.db_manager.list_artifacts(self.id)

    def get_lineage(self, depth: int = 3) -> dict:
        """Get lineage graph for this entry."""
        ancestors = self.workspace.db_manager.get_ancestors(self.id, depth)
        descendants = self.workspace.db_manager.get_descendants(self.id, depth)

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
            if isinstance(value, dict) and key in new_inputs and isinstance(new_inputs[key], dict):
                new_inputs[key] = {**new_inputs[key], **value}
            else:
                new_inputs[key] = value

        # Get parent page
        page_data = self.workspace.db_manager.get_page(self.page_id)
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
        self.workspace.db_manager.add_lineage_edge(self.id, variation.id, "variation_of")

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
        page_data = self.workspace.db_manager.get_page(self.page_id)

        # Delete from database
        result = self.workspace.db_manager.delete_entry(self.id)

        # Delete from Git
        if page_data:
            notebook_id = page_data["notebook_id"]
            self.workspace.git_manager.delete_entry(notebook_id, self.page_id, self.id)

        return result

    def get_page(self) -> "Page":
        """Get the parent page."""
        from codex.core.page import Page

        page_data = self.workspace.db_manager.get_page(self.page_id)
        if page_data:
            return Page.from_dict(self.workspace, page_data)
        raise ValueError(f"Page {self.page_id} not found")
