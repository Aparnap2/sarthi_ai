"""Token budget manager for concurrency control."""

import asyncio
from typing import Set


class TokenBudgetManager:
    """Manages token budget for concurrent task execution."""

    def __init__(self, max_concurrent_tasks: int = 10) -> None:
        """Initialize the budget manager.

        Args:
            max_concurrent_tasks: Maximum number of concurrent tasks allowed
        """
        self.max_concurrent_tasks = max_concurrent_tasks
        self._active_tasks: Set[str] = set()
        self._lock = asyncio.Lock()

    async def acquire_task_slot(self, task_id: str) -> None:
        """Acquire a slot for the given task.

        Args:
            task_id: Unique task identifier

        Raises:
            RuntimeError: If budget is exhausted
        """
        async with self._lock:
            if len(self._active_tasks) >= self.max_concurrent_tasks:
                raise RuntimeError("Budget exhausted: maximum concurrent tasks reached")
            self._active_tasks.add(task_id)

    async def release_task_slot(self, task_id: str) -> None:
        """Release a slot for the given task.

        Args:
            task_id: Unique task identifier
        """
        async with self._lock:
            self._active_tasks.discard(task_id)

    @property
    def active_task_count(self) -> int:
        """Get the number of active tasks."""
        return len(self._active_tasks)

    @property
    def available_slots(self) -> int:
        """Get the number of available slots."""
        return self.max_concurrent_tasks - len(self._active_tasks)
