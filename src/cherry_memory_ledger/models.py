"""Domain models for accounting decisions that may be persisted as memory.

These models define the intended data boundary only. They do not perform
accounting, tax, reconciliation, or Sibyl Memory operations by themselves.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True, slots=True)
class Transaction:
    """A demo-safe transaction presented to the decision layer."""

    business_id: str
    transaction_id: str
    description: str
    amount: Decimal
    currency: str = "GBP"
    supplier: str | None = None
    occurred_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class AccountingTreatment:
    """A proposed or accountant-approved treatment for a transaction."""

    category: str
    vat_treatment: str | None = None
    reconciliation_action: str | None = None
    evidence_requirements: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AccountingDecisionMemory:
    """Structured memory candidate created from an approved decision.

    `scope_conditions` are essential: remembered decisions should only be
    reused when their approval scope still matches the new transaction.
    """

    memory_id: str | None
    business_id: str
    supplier: str | None
    source_transaction_id: str
    source_description: str
    original_treatment: AccountingTreatment
    approved_treatment: AccountingTreatment
    rationale: str
    approved_by_role: str
    approved_at: datetime
    scope_conditions: tuple[str, ...] = ()
    status: Literal["active", "superseded", "review"] = "active"
    supersedes_memory_id: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)
