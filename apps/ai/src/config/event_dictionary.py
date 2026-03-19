"""
Event Dictionary for Sarthi v1.0.

Maps every (source, event_type) pair to exactly one agent.
Enforced in code — unknown events raise UnknownEventError.

Note: In v1.0, routing is handled by agents, not static topics/SOPs.
This dictionary is kept for backward compatibility and migration.
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class DictionaryEntry:
    """Single event mapping entry (v1.0 schema)."""
    source:     str
    event_type: str  # Normalized event type (e.g., "PAYMENT_SUCCESS")
    agent_name: str  # Agent that handles this event
    employees:  List[str] = field(default_factory=list)


class UnknownEventError(KeyError):
    """Raised when event is not in dictionary."""
    pass


# Registry of events for Sarthi v1.0 (sample entries for migration)
_REGISTRY: List[DictionaryEntry] = [
    # ── RAZORPAY ──────────────────────────────────────────────
    DictionaryEntry("razorpay", "PAYMENT_SUCCESS", "FinanceAgent", ["Bookkeeper", "CFO"]),
    DictionaryEntry("razorpay", "PAYMENT_FAILURE", "FinanceAgent", ["AR/AP Clerk"]),
    DictionaryEntry("razorpay", "SUBSCRIPTION_ACTIVATED", "FinanceAgent", ["Bookkeeper", "CFO"]),
    DictionaryEntry("razorpay", "SUBSCRIPTION_CANCELLED", "FinanceAgent", ["CFO", "BI Analyst"]),

    # ── TELEGRAM ──────────────────────────────────────────────
    DictionaryEntry("telegram", "QUERY_INBOUND", "ChiefOfStaffAgent", ["Chief of Staff"]),
    DictionaryEntry("telegram", "BANK_STATEMENT", "FinanceAgent", ["Bookkeeper", "CFO"]),

    # ── CRON ──────────────────────────────────────────────────
    DictionaryEntry("cron", "WEEKLY_BRIEFING", "ChiefOfStaffAgent", ["Chief of Staff"]),
]


class EventDictionary:
    """
    Event dictionary for Sarthi v1.0.

    Resolves (source, event_type) pairs to their corresponding
    agent and responsible employees.

    Usage:
        d = EventDictionary()
        entry = d.resolve("razorpay", "PAYMENT_SUCCESS")
        print(entry.agent_name)  # "FinanceAgent"
        print(entry.employees)   # ["Bookkeeper", "CFO"]
    """

    def __init__(self):
        self._index = {(e.source, e.event_type): e for e in _REGISTRY}

    def resolve(self, source: str, event_type: str) -> DictionaryEntry:
        """
        Resolve (source, event_type) to DictionaryEntry.

        Args:
            source: Event source (e.g., "razorpay", "stripe")
            event_type: Normalized event type (e.g., "PAYMENT_SUCCESS")

        Returns:
            DictionaryEntry with agent_name and employees

        Raises:
            UnknownEventError: If (source, event_type) not in dictionary
        """
        key = (source, event_type)
        if key not in self._index:
            raise UnknownEventError(
                f"No mapping for source='{source}' event_type='{event_type}'. "
                f"Add it to event_dictionary.py before handling."
            )
        return self._index[key]

    def all_entries(self) -> List[DictionaryEntry]:
        """Return all dictionary entries."""
        return list(self._index.values())

    def count(self) -> int:
        """Return total number of registered events."""
        return len(self._index)
