"""Task extension - task queue implementations."""

import asyncio
import uuid
from datetime import datetime

from deerflow_core.core.task import Task, TaskQueue, TaskResult, TaskStatus

__all__ = ["Task", "TaskQueue", "TaskResult", "TaskStatus", "SimpleTaskQueue"]


class SimpleTaskQueue(TaskQueue):
    """Simple in-memory task queue implementation.

    Executes tasks asynchronously and stores results in memory.

    Example:
        queue = SimpleTaskQueue()
        task_id = await queue.submit(MyTask("do something"))
        result = await queue.get_result(task_id)
    """

    def __init__(self):
        self._tasks: dict[str, Task] = {}
        self._results: dict[str, TaskResult] = {}
        self._lock = asyncio.Lock()

    async def submit(self, task: Task) -> str:
        """Submit a task for execution.

        Args:
            task: The task to submit.

        Returns:
            The task ID.
        """
        task_id = str(uuid.uuid4())[:8]

        async with self._lock:
            self._tasks[task_id] = task
            self._results[task_id] = TaskResult(
                task_id=task_id,
                status=TaskStatus.PENDING,
            )

        # Execute task asynchronously
        asyncio.create_task(self._run_task(task_id, task))

        return task_id

    async def _run_task(self, task_id: str, task: Task) -> None:
        """Run a task and store its result."""
        # Mark as running
        async with self._lock:
            self._results[task_id].status = TaskStatus.RUNNING
            self._results[task_id].started_at = datetime.now()

        try:
            # Execute the task
            result = await task.execute(None)

            # Override task_id to match queue's task_id
            result.task_id = task_id

            async with self._lock:
                self._results[task_id] = result
                if result.completed_at is None:
                    result.completed_at = datetime.now()

        except Exception as e:
            async with self._lock:
                self._results[task_id].status = TaskStatus.FAILED
                self._results[task_id].error = str(e)
                self._results[task_id].completed_at = datetime.now()

    async def get_result(self, task_id: str) -> TaskResult | None:
        """Get the result of a submitted task.

        Args:
            task_id: The task ID.

        Returns:
            TaskResult if found, None otherwise.
        """
        async with self._lock:
            return self._results.get(task_id)

    async def list_tasks(self) -> list[TaskResult]:
        """List all tasks in the queue.

        Returns:
            List of TaskResult objects.
        """
        async with self._lock:
            return list(self._results.values())

    async def cancel(self, task_id: str) -> bool:
        """Cancel a task.

        Args:
            task_id: The task ID to cancel.

        Returns:
            True if cancelled, False if not found.
        """
        async with self._lock:
            if task_id not in self._tasks:
                return False

            task = self._tasks[task_id]
            task.cancel()

            self._results[task_id].status = TaskStatus.CANCELLED
            self._results[task_id].completed_at = datetime.now()

            return True
