# Cherry Memory Ledger

**Accounting decisions that compound, instead of disappearing.**

Cherry Memory Ledger is the Sibyl-powered memory layer for **Cherry Money**, an existing accounting and Open Banking application. The hackathon work makes accountant-approved corrections and reconciliation decisions survive genuinely fresh sessions and influence later transactions.

The public demo is deliberately self-contained so judges can reproduce the memory proof. The real product integration is layered onto the existing private Cherry Money application rather than rebuilding invoices, bank feeds, reconciliation or ledger posting from scratch.

## Product architecture

There are two deliberate repository boundaries:

### Existing product base — Prior Work

`sohamtech-uk/cherrymoney` is the private, pre-existing Cherry Money application. It already contains:

- Open Banking / Finexer transaction ingestion
- `OpenBankingTransaction`
- invoices and expenses
- `SmartBankMatcher` reconciliation suggestions
- chart of accounts / `LedgerAccount`
- `BankLedgerPostingService` double-entry posting
- authentication, company tenancy and the existing Transactions UI

Those features pre-date the Sibyl Labs hackathon and are **not** claimed as new work.

### New hackathon memory layer

This public repository contains the new Sibyl-specific capability and reproducible judging evidence:

- structured accountant-decision memory model
- real Sibyl `set_entity(...)` persistence
- append-only `write_event(...)` audit event
- `get_entity(...)` and FTS5 `search_entities(...)` recall
- a decision fork where recalled memory changes the accounting result
- a fresh-session acceptance test
- a deletion/no-memory counterfactual
- a public Vercel demo with visible timestamp and deployed commit proof

See [`docs/cherrymoney-base-integration.md`](docs/cherrymoney-base-integration.md) for the composition with the real product.

## What breaks when memory is deleted?

Without Sibyl Memory, Cherry loses the **company-specific accountant-approved knowledge** learned in earlier sessions. A future transaction falls back to Cherry Money's ordinary heuristic/default path instead of reusing the accountant's prior allocation, VAT/reconciliation treatment and rationale.

That is the load-bearing capability: Cherry Money still exists as prior work, but **learned accountant behaviour across fresh sessions disappears** when Sibyl Memory is removed.

The public demo makes this counterfactual visible: delete the Sibyl snapshot and the same Session B transaction returns to the generic `General Expenses` path.

## Current Sibyl implementation

The core loop is implemented and tested:

- **Persist:** `MemoryClient.set_entity(...)` stores the current accountant-approved supplier rule.
- **Audit:** `write_event(...)` records the approval in Sibyl's COLD journal.
- **Fresh session:** the original client/session is discarded; a later request constructs a new `MemoryClient` from persisted Sibyl bytes.
- **Recall:** `get_entity(...)` handles exact supplier recall; `search_entities(...)` provides FTS5 content recall where appropriate.
- **Changed decision:** recalled memory replaces the generic baseline with the accountant-approved treatment.
- **Counterfactual:** empty/deleted memory produces the baseline result instead.
- **Traceability:** the UI shows memory id, approval details, UTC observation time and deployed commit.

## Judge walkthrough

> **Persist:** An accountant changes an AWS transaction from a generic treatment to an approved accounting treatment and Cherry persists the structured decision as a Sibyl entity plus audit event.  
> **Recall (fresh session):** Session A ends. Session B creates a new Sibyl client and recalls the prior AWS decision without the user re-entering it.  
> **Changes the agent's decision by:** A related AWS transaction uses the remembered treatment. Remove the memory and the same transaction reverts to the ordinary baseline.

In the real Cherry Money integration, the baseline is the existing `SmartBankMatcher`; the human-approved target is an actual Cherry Money `LedgerAccount`; the existing `BankLedgerPostingService` remains responsible for accounting entries.

## Load-bearing code pointers

The public Sibyl path is intentionally concentrated for quick judging:

- **Writes:** `src/cherry_memory_ledger/memory_gateway.py` → `SibylMemoryGateway.persist_accounting_decision(...)`
  - `set_entity(...)`
  - `write_event(...)`
- **Reads:** `src/cherry_memory_ledger/memory_gateway.py` → `SibylMemoryGateway.recall_relevant_decisions(...)`
  - `get_entity(...)`
  - `search_entities(...)`
- **Decision change:** `src/cherry_memory_ledger/decision_engine.py` → `decide(...)`
  - no memory → generic baseline
  - recalled memory → accountant-approved treatment

## Real Cherry Money write path

The private hackathon integration uses existing Cherry Money functionality rather than replacing it:

1. Existing bank transaction enters Cherry Money.
2. Existing `SmartBankMatcher` gives the normal suggestion.
3. Human accountant selects the correct existing ledger account.
4. Existing `BankLedgerPostingService` performs the accounting posting.
5. If **Remember with Sibyl** is selected, the approved allocation and scope are sent to this service.
6. This service updates Sibyl Memory and returns the local-first SQLite snapshot.
7. Cherry Money encrypts that opaque snapshot at rest with Laravel application encryption and stores it in a dedicated `sibyl_memory_snapshots` row keyed by Cherry Money company id.

Memory failure never rolls back a successful ledger posting.

## Real Cherry Money fresh-session recall

On a later request:

1. Cherry Money first calculates its ordinary `SmartBankMatcher` baseline.
2. The company's encrypted `sibyl_memory_snapshots` state row is loaded and decrypted server-side.
3. This stateless service receives the snapshot and constructs a new Sibyl client.
4. The relevant accountant decision is recalled.
5. When a memory matches, the remembered allocation and provenance enrich/replace the generic suggestion.
6. Any final accounting action still goes through Cherry Money's existing workflow.

This makes the no-memory comparison clean: **same Cherry Money product, same transaction, same existing matcher — only the learned accountant memory changes.**

The dedicated state table is intentional: Cherry Money's legacy `company` row is already very wide, while reusing an unrelated audit/settings table would weaken its semantics. The private integration preserves the checksum-bound historical Phase-4 fixture and explicitly validates the new table as post-baseline zero-row schema.

## Public Vercel demo

Live demo: `https://cherry-memory-ledger-one.vercel.app/`

The public Vercel demo uses synthetic transactions and the following sequence:

1. Session A starts with `AMZN AWS EMEA 120.00 GBP` on the generic path.
2. Accountant approves the corrected category plus VAT/evidence/reconciliation rule.
3. Click **Approve & save to Sibyl Memory**.
4. Click **End Session A → Start Session B**; the page reloads.
5. Session B receives `AWS EMEA SARL 240.00 GBP` without re-explanation.
6. Click **Ask Cherry in this fresh session**.
7. The result shows the recalled memory, changed decision, UTC observation timestamp and deployed commit.
8. Click **Delete memory & run counterfactual**; the same flow falls back to the baseline.

All public-demo transactions are synthetic. The prototype is not tax or accounting advice.

## Why the public demo carries SQLite in browser storage

Sibyl Memory is local-first and SQLite-backed, while Vercel function filesystems are ephemeral. The public judging demo therefore checkpoints Sibyl's WAL and carries the small SQLite snapshot between stateless requests through browser `localStorage`.

All actual memory operations are still performed by the official `sibyl-memory-client`; browser storage is only the transport used to make the public serverless proof durable across reloads/cold starts.

**The real Cherry Money integration does not use browser storage for accounting memory.** It encrypts the returned Sibyl snapshot and persists it server-side in a company-scoped `sibyl_memory_snapshots` row.

## Memory model

`AccountingDecisionMemory` stores structured decisions, not merely chat text:

- business identifier
- supplier/counterparty
- source transaction and description
- original proposed treatment
- accountant-approved treatment
- VAT/evidence requirements
- reconciliation action
- rationale
- approval role/time
- reuse scope conditions
- active/superseded/review status
- tags and supersession metadata

## Sibyl primitives actually exercised

This build claims only behaviours that exist in code:

- **entities / structured memory** — WARM `set_entity`
- **recall** — `get_entity`
- **search** — FTS5 `search_entities`
- **journal / temporal audit** — COLD `write_event`

We do **not** claim embedding-based semantic search, reflection, consolidation or time-travel until those behaviours are genuinely implemented and demonstrated.

## Tests

`tests/test_memory_acceptance.py` exercises the real Sibyl client:

- Session A persists an accountant decision
- Session A is discarded
- Session B constructs a new gateway/client against persisted Sibyl bytes
- Session B recalls the rule
- the decision changes to the approved treatment
- the same transaction against empty memory follows the baseline
- FTS5 recall is exercised for a related description when no supplier field is available

Run locally:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
uvicorn app:app --reload
```

## Repository layout

```text
.
├── app.py
├── docs/
│   ├── architecture.md
│   ├── cherrymoney-base-integration.md
│   └── demo-script.md
├── src/cherry_memory_ledger/
│   ├── decision_engine.py
│   ├── memory_gateway.py
│   └── models.py
├── tests/
│   └── test_memory_acceptance.py
├── LICENSE
└── pyproject.toml
```

## Partner stacks

### Base — planned, not implemented

Potential next step: anchor a cryptographic fingerprint of an accountant-approved memory/audit event on Base while keeping detailed accounting context in Sibyl Memory. No Base multiplier is claimed until a real on-chain action is implemented and exercised.

### Virtuals Protocol — planned, not implemented

Potential next step: coordinate a bookkeeping agent and an accounting-review agent around memory-backed exceptions. No Virtuals integration is claimed yet.

## Prior Work declaration

Cherry Money's private Laravel application, brand, Open Banking, invoicing/expense functionality, `SmartBankMatcher`, ledger/chart-of-accounts implementation and other normal product capabilities existed before the Sibyl Labs hackathon.

New hackathon work includes this public `cherry-memory-ledger` repository's Sibyl adapter, decision-memory model, fresh-session proof, tests and public demo, plus the explicit Memory Ledger integration layer being developed on top of Cherry Money. Existing Cherry Money functionality is reused as **Prior Work**, not presented as newly created hackathon code.

## Licence

MIT. See `LICENSE`.
