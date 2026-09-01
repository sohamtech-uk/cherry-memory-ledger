"""Sibyl Memory integration boundary for Cherry Memory Ledger.

This module contains the hackathon's load-bearing memory writes and reads.
Accountant-approved decisions are stored as Sibyl WARM entities, while an
append-only journal event records each approval for audit/history. A fresh
`SibylMemoryGateway` can reopen the same Sibyl SQLite file and recall the rule.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from sibyl_memory_client import MemoryClient
from sibyl_memory_client.exceptions import NotFoundError

from .models import AccountingDecisionMemory, AccountingTreatment, Transaction

DECISION_CATEGORY = "accounting_decision"


class MemoryGateway(Protocol):
    """Port used by the accounting decision layer."""

    def persist_accounting_decision(
        self, memory: AccountingDecisionMemory
    ) -> str:
        """Persist an accountant-approved decision and return its logical key."""
        ...

    def recall_relevant_decisions(
        self, transaction: Transaction
    ) -> list[AccountingDecisionMemory]:
        """Recall memories relevant to a new transaction in a fresh session."""
        ...


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:120] or "unknown"


def _entity_name(memory: AccountingDecisionMemory) -> str:
    subject = memory.supplier or memory.source_description
    return f"{_slug(memory.business_id)}:{_slug(subject)}"


def _transaction_entity_name(transaction: Transaction) -> str | None:
    if not transaction.supplier:
        return None
    return f"{_slug(transaction.business_id)}:{_slug(transaction.supplier)}"


def _treatment_to_dict(treatment: AccountingTreatment) -> dict[str, Any]:
    return {
        "category": treatment.category,
        "vat_treatment": treatment.vat_treatment,
        "reconciliation_action": treatment.reconciliation_action,
        "evidence_requirements": list(treatment.evidence_requirements),
    }


def _treatment_from_dict(payload: dict[str, Any]) -> AccountingTreatment:
    return AccountingTreatment(
        category=str(payload.get("category") or "General Expenses"),
        vat_treatment=payload.get("vat_treatment"),
        reconciliation_action=payload.get("reconciliation_action"),
        evidence_requirements=tuple(payload.get("evidence_requirements") or ()),
    )


def _memory_to_body(memory: AccountingDecisionMemory, logical_key: str) -> dict[str, Any]:
    return {
        "memory_id": logical_key,
        "business_id": memory.business_id,
        "supplier": memory.supplier,
        "source_transaction_id": memory.source_transaction_id,
        "source_description": memory.source_description,
        "original_treatment": _treatment_to_dict(memory.original_treatment),
        "approved_treatment": _treatment_to_dict(memory.approved_treatment),
        "rationale": memory.rationale,
        "approved_by_role": memory.approved_by_role,
        "approved_at": memory.approved_at.isoformat(),
        "scope_conditions": list(memory.scope_conditions),
        "status": memory.status,
        "supersedes_memory_id": memory.supersedes_memory_id,
        "tags": list(memory.tags),
        # This field intentionally repeats the important natural-language terms
        # so Sibyl's FTS5 search can find related rules when an exact supplier
        # entity lookup is unavailable.
        "search_text": " ".join(
            part
            for part in (
                memory.supplier,
                memory.source_description,
                memory.approved_treatment.category,
                memory.approved_treatment.vat_treatment,
                memory.rationale,
                " ".join(memory.tags),
            )
            if part
        ),
    }


def _memory_from_row(row: dict[str, Any]) -> AccountingDecisionMemory:
    body = row.get("body") or {}
    if not isinstance(body, dict):
        raise ValueError("Sibyl accounting-decision entity body is not a mapping")

    approved_at_raw = body.get("approved_at")
    approved_at = (
        datetime.fromisoformat(approved_at_raw)
        if isinstance(approved_at_raw, str)
        else datetime.utcnow()
    )

    return AccountingDecisionMemory(
        memory_id=str(body.get("memory_id") or row.get("name") or row.get("id")),
        business_id=str(body.get("business_id") or "demo"),
        supplier=body.get("supplier"),
        source_transaction_id=str(body.get("source_transaction_id") or "unknown"),
        source_description=str(body.get("source_description") or ""),
        original_treatment=_treatment_from_dict(body.get("original_treatment") or {}),
        approved_treatment=_treatment_from_dict(body.get("approved_treatment") or {}),
        rationale=str(body.get("rationale") or "Accountant-approved prior decision"),
        approved_by_role=str(body.get("approved_by_role") or "accountant"),
        approved_at=approved_at,
        scope_conditions=tuple(body.get("scope_conditions") or ()),
        status=body.get("status") or "active",
        supersedes_memory_id=body.get("supersedes_memory_id"),
        tags=tuple(body.get("tags") or ()),
    )


class SibylMemoryGateway:
    """Real Sibyl Memory adapter backed by the official Python client.

    The adapter deliberately opens a local SQLite-backed `MemoryClient`. That
    makes the fresh-session test meaningful: a new gateway object can reopen
    the same memory file without any Python object/session state from the
    original write.
    """

    def __init__(self, db_path: str | Path, *, tenant_id: str | None = None) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        kwargs: dict[str, Any] = {}
        if tenant_id:
            kwargs["tenant_id"] = tenant_id
        self._client = MemoryClient.local(str(self.db_path), **kwargs)

    def persist_accounting_decision(
        self, memory: AccountingDecisionMemory
    ) -> str:
        logical_key = memory.memory_id or _entity_name(memory)
        body = _memory_to_body(memory, logical_key)

        # LOAD-BEARING SIBYL WRITE #1: WARM entity, one current rule per
        # business + supplier. Re-approval of the same supplier intentionally
        # upserts the current source of truth.
        self._client.set_entity(
            DECISION_CATEGORY,
            logical_key,
            body,
            status=memory.status,
        )

        # LOAD-BEARING SIBYL WRITE #2: COLD journal audit trail. The entity is
        # the current rule; the journal preserves that an approval occurred.
        self._client.write_event(
            acted=[
                "Accountant approved accounting treatment: "
                f"{memory.approved_treatment.category} for "
                f"{memory.supplier or memory.source_description} "
                f"(memory {logical_key})"
            ]
        )
        return logical_key

    def recall_relevant_decisions(
        self, transaction: Transaction
    ) -> list[AccountingDecisionMemory]:
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()

        # LOAD-BEARING SIBYL READ #1: exact entity recall for a known supplier.
        exact_name = _transaction_entity_name(transaction)
        if exact_name:
            try:
                row = self._client.get_entity(DECISION_CATEGORY, exact_name)
                if row:
                    rows.append(row)
                    seen.add(str(row.get("id") or row.get("name") or exact_name))
            except NotFoundError:
                pass

        # LOAD-BEARING SIBYL READ #2: FTS5 recall for related descriptions.
        # Searching a few high-signal terms separately is intentional because
        # Sibyl's default FTS mode ANDs query tokens; a related bank description
        # may contain extra words that were not present in the original one.
        candidates: list[str] = []
        if transaction.supplier:
            candidates.append(transaction.supplier)
        candidates.extend(
            token
            for token in re.findall(r"[A-Za-z0-9]{3,}", transaction.description)
            if token.lower() not in {"the", "and", "for", "ltd", "limited", "payment"}
        )

        for query in candidates[:6]:
            try:
                hits = self._client.search_entities(
                    query,
                    category=DECISION_CATEGORY,
                    limit=5,
                )
            except Exception:
                # Exact recall above remains useful if a search term is rejected
                # by the FTS validator. Storage/backend errors are intentionally
                # not swallowed elsewhere in the gateway.
                continue
            for row in hits:
                row_id = str(row.get("id") or row.get("name") or "")
                if row_id and row_id not in seen:
                    rows.append(row)
                    seen.add(row_id)

        memories: list[AccountingDecisionMemory] = []
        for row in rows:
            memory = _memory_from_row(row)
            if memory.business_id != transaction.business_id:
                continue
            if memory.status != "active":
                continue
            memories.append(memory)

        memories.sort(key=lambda item: item.approved_at, reverse=True)
        return memories
