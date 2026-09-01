"""Small, inspectable accounting decision layer for the hackathon demo.

This is intentionally not a full accounting engine. Its purpose is to make the
memory counterfactual obvious: without a relevant Sibyl memory the transaction
gets a generic baseline; with an accountant-approved memory the outcome changes
and exposes exactly which memory caused that change.
"""

from __future__ import annotations

from dataclasses import dataclass

from .memory_gateway import MemoryGateway
from .models import AccountingDecisionMemory, AccountingTreatment, Transaction


@dataclass(frozen=True, slots=True)
class DecisionOutcome:
    treatment: AccountingTreatment
    source: str
    rationale: str
    memory: AccountingDecisionMemory | None = None

    @property
    def used_memory(self) -> bool:
        return self.memory is not None


def default_treatment(_: Transaction) -> AccountingTreatment:
    """Memory-free baseline used for the judge-visible counterfactual."""
    return AccountingTreatment(
        category="General Expenses",
        vat_treatment="Review VAT evidence before reclaiming input VAT",
        reconciliation_action="Leave unmatched for routine bookkeeping review",
        evidence_requirements=("Supplier invoice or receipt",),
    )


def decide(transaction: Transaction, memory_gateway: MemoryGateway) -> DecisionOutcome:
    """Choose a treatment, making recalled Sibyl memory load-bearing."""
    memories = memory_gateway.recall_relevant_decisions(transaction)
    if not memories:
        return DecisionOutcome(
            treatment=default_treatment(transaction),
            source="default",
            rationale=(
                "No relevant accountant-approved memory was recalled, so Cherry "
                "fell back to its generic bookkeeping baseline."
            ),
        )

    memory = memories[0]
    return DecisionOutcome(
        treatment=memory.approved_treatment,
        source="sibyl_memory",
        rationale=(
            f"Recalled accountant-approved memory {memory.memory_id}: "
            f"{memory.rationale}"
        ),
        memory=memory,
    )
