"""Acceptance tests for the load-bearing Sibyl Memory proof."""

from datetime import datetime, timezone
from decimal import Decimal

from cherry_memory_ledger.decision_engine import decide
from cherry_memory_ledger.memory_gateway import SibylMemoryGateway
from cherry_memory_ledger.models import (
    AccountingDecisionMemory,
    AccountingTreatment,
    Transaction,
)


def test_persist_fresh_session_recall_changes_decision(tmp_path) -> None:
    """Persist -> reconstruct gateway -> recall -> materially changed decision."""
    db_path = tmp_path / "sibyl-memory.db"

    session_a = SibylMemoryGateway(db_path)
    memory_id = session_a.persist_accounting_decision(
        AccountingDecisionMemory(
            memory_id=None,
            business_id="demo-company",
            supplier="AWS",
            source_transaction_id="txn-session-a",
            source_description="AMZN AWS EMEA 120.00 GBP",
            original_treatment=AccountingTreatment(
                category="General Expenses",
                vat_treatment="Review VAT evidence before reclaiming input VAT",
            ),
            approved_treatment=AccountingTreatment(
                category="Software & Cloud Services",
                vat_treatment="Reclaim input VAT only when a valid VAT invoice is held",
                reconciliation_action="Match to monthly cloud-services invoice",
                evidence_requirements=("Valid VAT invoice",),
            ),
            rationale="AWS is an approved recurring cloud-software supplier.",
            approved_by_role="accountant",
            approved_at=datetime.now(timezone.utc),
            scope_conditions=("Supplier is AWS", "Valid VAT invoice required for VAT reclaim"),
            tags=("aws", "cloud", "software", "vat"),
        )
    )
    assert memory_id == "demo-company:aws"

    # Fresh-session boundary: discard Session A and construct a brand-new
    # gateway/client against only the persisted Sibyl SQLite file.
    del session_a
    session_b = SibylMemoryGateway(db_path)

    later_transaction = Transaction(
        business_id="demo-company",
        transaction_id="txn-session-b",
        description="AWS EMEA SARL 240.00 GBP",
        supplier="AWS",
        amount=Decimal("240.00"),
    )
    remembered = decide(later_transaction, session_b)

    assert remembered.source == "sibyl_memory"
    assert remembered.used_memory is True
    assert remembered.memory is not None
    assert remembered.memory.memory_id == "demo-company:aws"
    assert remembered.treatment.category == "Software & Cloud Services"
    assert "valid VAT invoice" in (remembered.treatment.vat_treatment or "")

    # Counterfactual: the same transaction against an empty Sibyl memory loses
    # the learned treatment and reverts to the generic baseline.
    no_memory_session = SibylMemoryGateway(tmp_path / "empty-sibyl-memory.db")
    counterfactual = decide(later_transaction, no_memory_session)

    assert counterfactual.source == "default"
    assert counterfactual.used_memory is False
    assert counterfactual.treatment.category == "General Expenses"
    assert counterfactual.treatment.category != remembered.treatment.category


def test_related_description_can_be_recalled_by_sibyl_fts(tmp_path) -> None:
    """If a supplier field is absent, FTS recall can still find a related rule."""
    db_path = tmp_path / "sibyl-memory.db"
    writer = SibylMemoryGateway(db_path)
    writer.persist_accounting_decision(
        AccountingDecisionMemory(
            memory_id="demo-company:github",
            business_id="demo-company",
            supplier="GitHub",
            source_transaction_id="txn-1",
            source_description="GITHUB INC MONTHLY PLAN",
            original_treatment=AccountingTreatment(category="General Expenses"),
            approved_treatment=AccountingTreatment(category="Software & Cloud Services"),
            rationale="GitHub is a recurring software subscription.",
            approved_by_role="accountant",
            approved_at=datetime.now(timezone.utc),
            tags=("github", "software", "subscription"),
        )
    )

    reader = SibylMemoryGateway(db_path)
    transaction = Transaction(
        business_id="demo-company",
        transaction_id="txn-2",
        description="GITHUB TEAM SUBSCRIPTION",
        supplier=None,
        amount=Decimal("35.00"),
    )

    outcome = decide(transaction, reader)
    assert outcome.source == "sibyl_memory"
    assert outcome.treatment.category == "Software & Cloud Services"
