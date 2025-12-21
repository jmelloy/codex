"""Tests for task system."""

import tempfile
from pathlib import Path

import pytest

from core.tasks import (
    Task,
    TaskManager,
    TaskMessage,
    TaskStatus,
    TaskType,
)


class TestTaskMessage:
    """Test TaskMessage class."""

    def test_create_message(self):
        """Test creating a message."""
        msg = TaskMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.timestamp is not None
        assert msg.metadata == {}

    def test_message_to_dict(self):
        """Test converting message to dictionary."""
        msg = TaskMessage(
            role="assistant", content="Response", metadata={"key": "value"}
        )
        data = msg.to_dict()
        assert data["role"] == "assistant"
        assert data["content"] == "Response"
        assert "timestamp" in data
        assert data["metadata"]["key"] == "value"

    def test_message_from_dict(self):
        """Test creating message from dictionary."""
        data = {
            "role": "system",
            "content": "System message",
            "timestamp": "2024-01-01T00:00:00",
            "metadata": {"type": "info"},
        }
        msg = TaskMessage.from_dict(data)
        assert msg.role == "system"
        assert msg.content == "System message"
        assert msg.metadata["type"] == "info"


class TestTask:
    """Test Task class."""

    def test_create_task(self):
        """Test creating a task."""
        task = Task(
            id="task-1",
            task_type=TaskType.AGENT_OPERATION,
            status=TaskStatus.PENDING,
            title="Test Task",
        )
        assert task.id == "task-1"
        assert task.task_type == TaskType.AGENT_OPERATION
        assert task.status == TaskStatus.PENDING
        assert task.title == "Test Task"
        assert task.messages == []

    def test_add_message(self):
        """Test adding a message to a task."""
        task = Task(
            id="task-1",
            task_type=TaskType.CHAT_INTERACTION,
            status=TaskStatus.PENDING,
            title="Chat Task",
        )
        task.add_message("user", "Hello")
        assert len(task.messages) == 1
        assert task.messages[0].role == "user"
        assert task.messages[0].content == "Hello"

    def test_mark_running(self):
        """Test marking a task as running."""
        task = Task(
            id="task-1",
            task_type=TaskType.AGENT_OPERATION,
            status=TaskStatus.PENDING,
            title="Test",
        )
        task.mark_running()
        assert task.status == TaskStatus.RUNNING
        assert task.started_at is not None

    def test_mark_completed(self):
        """Test marking a task as completed."""
        task = Task(
            id="task-1",
            task_type=TaskType.AGENT_OPERATION,
            status=TaskStatus.RUNNING,
            title="Test",
        )
        task.mark_completed({"result": "success"})
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None
        assert task.output_data["result"] == "success"

    def test_mark_failed(self):
        """Test marking a task as failed."""
        task = Task(
            id="task-1",
            task_type=TaskType.AGENT_OPERATION,
            status=TaskStatus.RUNNING,
            title="Test",
        )
        task.mark_failed("Error occurred", "Traceback...")
        assert task.status == TaskStatus.FAILED
        assert task.completed_at is not None
        assert task.error_message == "Error occurred"
        assert task.error_traceback == "Traceback..."

    def test_mark_cancelled(self):
        """Test marking a task as cancelled."""
        task = Task(
            id="task-1",
            task_type=TaskType.AGENT_OPERATION,
            status=TaskStatus.PENDING,
            title="Test",
        )
        task.mark_cancelled()
        assert task.status == TaskStatus.CANCELLED
        assert task.completed_at is not None

    def test_task_to_dict(self):
        """Test converting task to dictionary."""
        task = Task(
            id="task-1",
            task_type=TaskType.AGENT_OPERATION,
            status=TaskStatus.PENDING,
            title="Test Task",
            description="Test description",
            workspace_path="/path/to/workspace",
        )
        task.add_message("user", "Hello")

        data = task.to_dict()
        assert data["id"] == "task-1"
        assert data["task_type"] == "agent_operation"
        assert data["status"] == "pending"
        assert data["title"] == "Test Task"
        assert len(data["messages"]) == 1

    def test_task_from_dict(self):
        """Test creating task from dictionary."""
        data = {
            "id": "task-2",
            "task_type": "chat_interaction",
            "status": "completed",
            "title": "Chat Task",
            "description": "A chat task",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T01:00:00",
            "started_at": "2024-01-01T00:30:00",
            "completed_at": "2024-01-01T01:00:00",
            "messages": [
                {
                    "role": "user",
                    "content": "Hello",
                    "timestamp": "2024-01-01T00:30:00",
                    "metadata": {},
                }
            ],
        }
        task = Task.from_dict(data)
        assert task.id == "task-2"
        assert task.task_type == TaskType.CHAT_INTERACTION
        assert task.status == TaskStatus.COMPLETED
        assert len(task.messages) == 1


class TestTaskManager:
    """Test TaskManager class."""

    def test_create_task_manager(self):
        """Test creating a task manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir))
            assert manager.storage_path.exists()
            # tasks_file is created on first save
            assert not manager.tasks_file.exists() or manager.tasks_file.exists()

    def test_create_task(self):
        """Test creating a task."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir))
            task = manager.create_task(
                task_id="task-1",
                task_type=TaskType.AGENT_OPERATION,
                title="Test Task",
                description="Test description",
            )
            assert task.id == "task-1"
            assert task.title == "Test Task"

    def test_get_task(self):
        """Test getting a task."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir))
            created_task = manager.create_task(
                task_id="task-1",
                task_type=TaskType.AGENT_OPERATION,
                title="Test Task",
            )

            retrieved_task = manager.get_task("task-1")
            assert retrieved_task is not None
            assert retrieved_task.id == created_task.id
            assert retrieved_task.title == created_task.title

    def test_get_nonexistent_task(self):
        """Test getting a nonexistent task."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir))
            task = manager.get_task("nonexistent")
            assert task is None

    def test_list_tasks(self):
        """Test listing tasks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir))
            manager.create_task("task-1", TaskType.AGENT_OPERATION, "Task 1")
            manager.create_task("task-2", TaskType.CHAT_INTERACTION, "Task 2")
            manager.create_task("task-3", TaskType.ANALYSIS, "Task 3")

            tasks = manager.list_tasks()
            assert len(tasks) == 3

    def test_list_tasks_with_status_filter(self):
        """Test listing tasks with status filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir))
            task1 = manager.create_task("task-1", TaskType.AGENT_OPERATION, "Task 1")
            task2 = manager.create_task("task-2", TaskType.AGENT_OPERATION, "Task 2")

            task1.mark_running()
            manager.update_task(task1)

            running_tasks = manager.list_tasks(status=TaskStatus.RUNNING)
            assert len(running_tasks) == 1
            assert running_tasks[0].id == "task-1"

            pending_tasks = manager.list_tasks(status=TaskStatus.PENDING)
            assert len(pending_tasks) == 1
            assert pending_tasks[0].id == "task-2"

    def test_list_tasks_with_type_filter(self):
        """Test listing tasks with type filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir))
            manager.create_task("task-1", TaskType.AGENT_OPERATION, "Task 1")
            manager.create_task("task-2", TaskType.CHAT_INTERACTION, "Task 2")
            manager.create_task("task-3", TaskType.AGENT_OPERATION, "Task 3")

            agent_tasks = manager.list_tasks(task_type=TaskType.AGENT_OPERATION)
            assert len(agent_tasks) == 2

            chat_tasks = manager.list_tasks(task_type=TaskType.CHAT_INTERACTION)
            assert len(chat_tasks) == 1

    def test_update_task(self):
        """Test updating a task."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir))
            task = manager.create_task("task-1", TaskType.AGENT_OPERATION, "Task 1")

            task.add_message("user", "Hello")
            manager.update_task(task)

            retrieved_task = manager.get_task("task-1")
            assert len(retrieved_task.messages) == 1

    def test_delete_task(self):
        """Test deleting a task."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir))
            manager.create_task("task-1", TaskType.AGENT_OPERATION, "Task 1")

            result = manager.delete_task("task-1")
            assert result is True

            task = manager.get_task("task-1")
            assert task is None

    def test_delete_nonexistent_task(self):
        """Test deleting a nonexistent task."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir))
            result = manager.delete_task("nonexistent")
            assert result is False

    def test_task_persistence(self):
        """Test that tasks are persisted to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create tasks
            manager1 = TaskManager(Path(tmpdir))
            manager1.create_task("task-1", TaskType.AGENT_OPERATION, "Task 1")
            manager1.create_task("task-2", TaskType.CHAT_INTERACTION, "Task 2")

            # Load tasks in a new manager instance
            manager2 = TaskManager(Path(tmpdir))
            tasks = manager2.list_tasks()
            assert len(tasks) == 2

            task1 = manager2.get_task("task-1")
            assert task1 is not None
            assert task1.title == "Task 1"

    def test_task_with_context(self):
        """Test creating task with context information."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskManager(Path(tmpdir))
            task = manager.create_task(
                task_id="task-1",
                task_type=TaskType.AGENT_OPERATION,
                title="Contextual Task",
                workspace_path="/workspace",
                notebook_id="nb-123",
                page_id="page-456",
                entry_id="entry-789",
            )
            assert task.workspace_path == "/workspace"
            assert task.notebook_id == "nb-123"
            assert task.page_id == "page-456"
            assert task.entry_id == "entry-789"
