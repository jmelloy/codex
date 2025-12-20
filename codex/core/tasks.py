"""Task system for agent and chat operations.

This module provides a task system for managing agent operations
and chat interactions within the Codex system.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pathlib import Path
import json


def _now() -> datetime:
    """Get current time without timezone info for SQLite compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TaskStatus(Enum):
    """Status of a task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(Enum):
    """Type of task."""

    AGENT_OPERATION = "agent_operation"
    CHAT_INTERACTION = "chat_interaction"
    FILE_MODIFICATION = "file_modification"
    ANALYSIS = "analysis"
    CUSTOM = "custom"


@dataclass
class TaskMessage:
    """A message in a task conversation."""

    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskMessage":
        """Create from dictionary."""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Task:
    """A task for agent or chat operations."""

    id: str
    task_type: TaskType
    status: TaskStatus
    title: str
    description: str = ""
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Task context
    workspace_path: Optional[str] = None
    notebook_id: Optional[str] = None
    page_id: Optional[str] = None
    entry_id: Optional[str] = None
    
    # Task data
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    messages: List[TaskMessage] = field(default_factory=list)
    
    # Agent configuration
    agent_config: Dict[str, Any] = field(default_factory=dict)
    
    # Error tracking
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            "id": self.id,
            "task_type": self.task_type.value,
            "status": self.status.value,
            "title": self.title,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "workspace_path": self.workspace_path,
            "notebook_id": self.notebook_id,
            "page_id": self.page_id,
            "entry_id": self.entry_id,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "messages": [msg.to_dict() for msg in self.messages],
            "agent_config": self.agent_config,
            "error_message": self.error_message,
            "error_traceback": self.error_traceback,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create task from dictionary."""
        return cls(
            id=data["id"],
            task_type=TaskType(data["task_type"]),
            status=TaskStatus(data["status"]),
            title=data["title"],
            description=data.get("description", ""),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            started_at=(
                datetime.fromisoformat(data["started_at"])
                if data.get("started_at")
                else None
            ),
            completed_at=(
                datetime.fromisoformat(data["completed_at"])
                if data.get("completed_at")
                else None
            ),
            workspace_path=data.get("workspace_path"),
            notebook_id=data.get("notebook_id"),
            page_id=data.get("page_id"),
            entry_id=data.get("entry_id"),
            input_data=data.get("input_data", {}),
            output_data=data.get("output_data", {}),
            messages=[TaskMessage.from_dict(m) for m in data.get("messages", [])],
            agent_config=data.get("agent_config", {}),
            error_message=data.get("error_message"),
            error_traceback=data.get("error_traceback"),
            metadata=data.get("metadata", {}),
        )

    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a message to the task.

        Args:
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional message metadata
        """
        self.messages.append(
            TaskMessage(role=role, content=content, metadata=metadata or {})
        )
        self.updated_at = _now()

    def mark_running(self) -> None:
        """Mark task as running."""
        self.status = TaskStatus.RUNNING
        self.started_at = _now()
        self.updated_at = _now()

    def mark_completed(self, output_data: Optional[Dict[str, Any]] = None) -> None:
        """Mark task as completed.

        Args:
            output_data: Optional output data from task execution
        """
        self.status = TaskStatus.COMPLETED
        self.completed_at = _now()
        self.updated_at = _now()
        if output_data:
            self.output_data.update(output_data)

    def mark_failed(self, error_message: str, error_traceback: Optional[str] = None) -> None:
        """Mark task as failed.

        Args:
            error_message: Error message
            error_traceback: Optional error traceback
        """
        self.status = TaskStatus.FAILED
        self.completed_at = _now()
        self.updated_at = _now()
        self.error_message = error_message
        self.error_traceback = error_traceback

    def mark_cancelled(self) -> None:
        """Mark task as cancelled."""
        self.status = TaskStatus.CANCELLED
        self.completed_at = _now()
        self.updated_at = _now()


class TaskManager:
    """Manager for task operations."""

    def __init__(self, storage_path: Path):
        """Initialize task manager.

        Args:
            storage_path: Path to store task data
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.tasks_file = self.storage_path / "tasks.json"
        self._tasks: Dict[str, Task] = {}
        self._load_tasks()

    def _load_tasks(self) -> None:
        """Load tasks from storage."""
        if self.tasks_file.exists():
            with open(self.tasks_file, "r") as f:
                data = json.load(f)
                self._tasks = {
                    task_id: Task.from_dict(task_data)
                    for task_id, task_data in data.items()
                }

    def _save_tasks(self) -> None:
        """Save tasks to storage."""
        with open(self.tasks_file, "w") as f:
            data = {task_id: task.to_dict() for task_id, task in self._tasks.items()}
            json.dump(data, f, indent=2)

    def create_task(
        self,
        task_id: str,
        task_type: TaskType,
        title: str,
        description: str = "",
        workspace_path: Optional[str] = None,
        notebook_id: Optional[str] = None,
        page_id: Optional[str] = None,
        entry_id: Optional[str] = None,
        input_data: Optional[Dict[str, Any]] = None,
        agent_config: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """Create a new task.

        Args:
            task_id: Unique task ID
            task_type: Type of task
            title: Task title
            description: Task description
            workspace_path: Optional workspace path
            notebook_id: Optional notebook ID
            page_id: Optional page ID
            entry_id: Optional entry ID
            input_data: Optional input data
            agent_config: Optional agent configuration
            metadata: Optional metadata

        Returns:
            Created task
        """
        task = Task(
            id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            title=title,
            description=description,
            workspace_path=workspace_path,
            notebook_id=notebook_id,
            page_id=page_id,
            entry_id=entry_id,
            input_data=input_data or {},
            agent_config=agent_config or {},
            metadata=metadata or {},
        )
        self._tasks[task_id] = task
        self._save_tasks()
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task or None if not found
        """
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        task_type: Optional[TaskType] = None,
        workspace_path: Optional[str] = None,
    ) -> List[Task]:
        """List tasks with optional filters.

        Args:
            status: Filter by status
            task_type: Filter by task type
            workspace_path: Filter by workspace path

        Returns:
            List of tasks
        """
        tasks = list(self._tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]
        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]
        if workspace_path:
            tasks = [t for t in tasks if t.workspace_path == workspace_path]

        # Sort by created_at descending
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks

    def update_task(self, task: Task) -> None:
        """Update a task.

        Args:
            task: Task to update
        """
        task.updated_at = _now()
        self._tasks[task.id] = task
        self._save_tasks()

    def delete_task(self, task_id: str) -> bool:
        """Delete a task.

        Args:
            task_id: Task ID

        Returns:
            True if deleted, False if not found
        """
        if task_id in self._tasks:
            del self._tasks[task_id]
            self._save_tasks()
            return True
        return False
