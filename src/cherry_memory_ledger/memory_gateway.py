"""Memory integration boundary.

The concrete Sibyl calls are intentionally NOT implemented in this scaffold.
The two methods on `SibylMemoryGateway` are the planned, easy-to-find write
and read points for the hackathon implementation.
"""

from __future__ import annotations

from typing import Protocol

from .models import AccountingDecisionMemory, Transaction


class MemoryGateway(Protocol):
    """Port used by the accounting decision layer."""

    def persist_accounting_decision(
        self, memory: AccountingDecisionMemory
    ) -> str:
        """Persist an accountant-approved decision and return its memory id."""
        ...

    def recall_relevant_decisions(
        self, transaction: Transaction
    ) -> list[AccountingDecisionMemory]:
        """Recall memories relevant to a new transaction in a fresh session."""
        ...


class SibylMemoryGateway:
    """Placeholder for the real Sibyl Memory adapter.

    No Sibyl SDK/API behaviour is claimed yet. These methods deliberately
    raise until the hackathon implementation has validated the supported
    client/API and mapped the domain model to real Sibyl primitives.
    """

    def persist_accounting_decision(
        self, memory: AccountingDecisionMemory
    ) -> str:
        # TODO(hackathon): replace with the validated Sibyl Memory write call.
        raise NotImplementedError("Sibyl Memory write is not implemented yet")

    def recall_relevant_decisions(
        self, transaction: Transaction
    ) -> list[AccountingDecisionMemory]:
        # TODO(hackathon): replace with validated Sibyl recall/search calls.
        raise NotImplementedError("Sibyl Memory recall is not implemented yet")
