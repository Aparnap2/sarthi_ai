"""Context store for state persistence."""

from typing import Any, Dict, Optional


class ContextStore:
    """Stores and retrieves context for agent workflows."""

    def __init__(self) -> None:
        """Initialize the context store."""
        self._data: Dict[str, Dict[str, Dict[str, Any]]] = {}

    async def write(
        self,
        task_id: str,
        agent: str,
        key: str,
        value: Any,
    ) -> None:
        """Write data to the context store.

        Args:
            task_id: Unique task identifier
            agent: Agent name
            key: Data key
            value: Data value
        """
        if task_id not in self._data:
            self._data[task_id] = {}
        if agent not in self._data[task_id]:
            self._data[task_id][agent] = {}
        self._data[task_id][agent][key] = value

    async def read(
        self,
        task_id: str,
        agent: Optional[str] = None,
        key: Optional[str] = None,
    ) -> Any:
        """Read data from the context store.

        Args:
            task_id: Unique task identifier
            agent: Optional agent name filter
            key: Optional key filter

        Returns:
            Stored data or None if not found
        """
        if task_id not in self._data:
            return None

        task_data = self._data[task_id]

        if agent is None:
            return task_data

        if agent not in task_data:
            return None

        agent_data = task_data[agent]

        if key is None:
            return agent_data

        return agent_data.get(key)

    async def clear(self, task_id: Optional[str] = None) -> None:
        """Clear data from the context store.

        Args:
            task_id: Optional task ID to clear. If None, clears all data.
        """
        if task_id is None:
            self._data.clear()
        elif task_id in self._data:
            del self._data[task_id]
