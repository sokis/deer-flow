"""Tests for task queue."""

import pytest
from datetime import datetime
from deerflow_core.core.task import Task, TaskQueue, TaskResult, TaskStatus
from deerflow_core.core.agent import Agent


class SimpleTask(Task):
    """A simple task for testing."""

    def __init__(self, description: str, task_id: str | None = None):
        super().__init__(description, task_id)
        self.executed = False

    async def execute(self, agent: Agent) -> TaskResult:
        self.executed = True
        return TaskResult(
            task_id=self.id,
            status=TaskStatus.COMPLETED,
            result={"message": "done"},
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )


class TestSimpleTaskQueue:
    """Tests for SimpleTaskQueue."""

    @pytest.fixture
    def queue(self):
        """Create a task queue instance."""
        from deerflow_core.extensions.task import SimpleTaskQueue
        return SimpleTaskQueue()

    @pytest.mark.asyncio
    async def test_submit_returns_task_id(self, queue):
        """submit() returns a task ID."""
        task = SimpleTask("Test task")
        task_id = await queue.submit(task)
        assert task_id is not None
        assert isinstance(task_id, str)

    @pytest.mark.asyncio
    async def test_get_result_after_submit(self, queue):
        """get_result() returns result after task is submitted."""
        task = SimpleTask("Test task")
        task_id = await queue.submit(task)

        # Wait for task to complete (async execution)
        import asyncio
        for _ in range(50):
            result = await queue.get_result(task_id)
            if result.status != TaskStatus.PENDING:
                break
            await asyncio.sleep(0.01)

        result = await queue.get_result(task_id)
        assert result is not None
        assert result.task_id == task_id
        assert result.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_get_result_not_found(self, queue):
        """get_result() returns None for unknown task ID."""
        result = await queue.get_result("unknown-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_tasks(self, queue):
        """list_tasks() returns all submitted tasks."""
        task1 = SimpleTask("Task 1")
        task2 = SimpleTask("Task 2")
        await queue.submit(task1)
        await queue.submit(task2)
        tasks = await queue.list_tasks()
        assert len(tasks) == 2

    @pytest.mark.asyncio
    async def test_cancel_task(self, queue):
        """cancel() cancels a pending task."""
        task = SimpleTask("Cancellable task")
        task_id = await queue.submit(task)
        cancelled = await queue.cancel(task_id)
        assert cancelled is True

    @pytest.mark.asyncio
    async def test_cancel_unknown_returns_false(self, queue):
        """cancel() returns False for unknown task."""
        cancelled = await queue.cancel("unknown-id")
        assert cancelled is False
