# Cherry Memory Ledger

**Accounting decisions that compound, instead of disappearing.**

Cherry Memory Ledger is a Sibyl Labs hackathon prototype for an accounting agent that remembers accountant-approved corrections, VAT treatments, reconciliation decisions, and business-specific rules across genuinely fresh sessions.

The core behaviour is intentionally easy to test: correct an AWS transaction once, end the session, then present a new AWS transaction. With Sibyl Memory, Cherry recalls the approved treatment and changes its decision. Delete the memory and the same transaction falls back to the generic baseline.

## What breaks when memory is deleted?

Without Sibyl Memory, Cherry loses the accountant-approved corrections, VAT treatments and reconciliation decisions that determine how future transactions are processed. Fresh sessions therefore revert to generic guesses and repeat previously corrected bookkeeping mistakes.

That counterfactual is implemented in the web demo: the **Delete memory & run counterfactual** action removes the Sibyl SQLite snapshot, and the exact same Session B decision returns to `General Expenses`.

## Current implementation status

The core Sibyl loop is now implemented on the `feat/sibyl-demo-ui` build:

- **Persist:** accountant-approved treatment is written to a Sibyl WARM entity with `MemoryClient.set_entity(...)`.
- **Audit:** the approval is also recorded in Sibyl's COLD journal using `write_event(...)`.
- **Fresh session:** the web page reloads, destroying JavaScript/session state, and the next API request constructs a brand-new `MemoryClient`.
- **Recall:** known suppliers use `get_entity(...)`; related descriptions can fall back to Sibyl FTS5 `search_entities(...)`.
- **Changed decision:** recalled memory replaces the generic treatment with the accountant-approved category/VAT/reconciliation treatment.
- **Counterfactual:** an empty/deleted Sibyl memory produces the generic decision instead.
- **Traceability:** the UI shows the logical memory key, approval role/time, rationale, and which Sibyl operations were exercised.

## Judge walkthrough

> **Persist:** An accountant changes an AWS transaction from `General Expenses` to `Software & Cloud Services`, approves a scoped VAT rule, and Cherry persists that structured decision as a Sibyl entity plus audit event.  
> **Recall (fresh session):** Session A is ended and the page reloads. Session B creates a new Sibyl client and recalls the AWS rule from the persisted SQLite memory without the user re-entering it.  
> **Changes the agent's decision by:** A related `AWS EMEA SARL` transaction is categorised as `Software & Cloud Services` with the remembered VAT/reconciliation treatment. Deleting the memory makes the same transaction revert to `General Expenses`.

## Load-bearing code pointers

The critical memory path is deliberately concentrated in one adapter so judges can verify it quickly:

- **Sibyl writes:** `src/cherry_memory_ledger/memory_gateway.py` → `SibylMemoryGateway.persist_accounting_decision(...)`
  - `set_entity(...)` stores the current accountant-approved supplier rule.
  - `write_event(...)` appends the approval to the journal/audit history.
- **Sibyl reads:** `src/cherry_memory_ledger/memory_gateway.py` → `SibylMemoryGateway.recall_relevant_decisions(...)`
  - `get_entity(...)` performs exact supplier recall.
  - `search_entities(...)` performs FTS5 recall when an exact supplier key is unavailable.
- **Decision change:** `src/cherry_memory_ledger/decision_engine.py` → `decide(...)`
  - no memory → generic `General Expenses` baseline
  - recalled memory → accountant-approved treatment

Removing or bypassing `SibylMemoryGateway` therefore materially changes the product's accounting result.

## Fresh-session persistence on Vercel

Sibyl Memory is local-first and SQLite-backed. Vercel function filesystems are ephemeral, so the demo does **not** pretend that `/tmp` is durable.

Instead, after every Sibyl write the API checkpoints Sibyl's WAL and returns the actual SQLite file as a base64 snapshot. The browser keeps that small demo snapshot in `localStorage`. A later request — including after a page reload or serverless cold start — writes those bytes to a fresh temporary file and constructs a brand-new official `MemoryClient` against it.

This is intentionally transparent in `app.py` (`_restore_snapshot` / `_encode_snapshot`). The memory schema, entity write, journal write, exact recall and FTS5 recall are all performed by `sibyl-memory-client`; browser storage is only the transport that carries Sibyl's local-first SQLite file between stateless Vercel requests.

For production Cherry Money, this demo transport would be replaced by an appropriately secured persistence model rather than storing accounting memory in browser localStorage.

## Memory model

`AccountingDecisionMemory` records structured decisions rather than a free-text chat transcript:

- demo-safe business identifier
- supplier/counterparty
- source transaction and description
- original proposed treatment
- accountant-approved treatment
- VAT treatment and evidence requirements
- reconciliation action
- rationale
- approval role/time
- reuse scope conditions
- active/superseded/review status
- tags and supersession metadata

For a supplier, the Sibyl WARM entity acts as the current source of truth. Re-approving the same supplier upserts that entity, while the COLD journal preserves an append-only audit event.

## Sibyl primitives actually exercised

This build currently claims only the operations that exist in code:

- **entities / structured memory** — WARM `set_entity`
- **recall** — `get_entity`
- **search** — FTS5 `search_entities`
- **journal / temporal audit trail** — COLD `write_event`

We do **not** claim embedding-based semantic search, reflection, consolidation, or time-travel until those behaviours are genuinely implemented and demonstrated.

## Web demo flow

1. **Session A:** synthetic `AMZN AWS EMEA 120.00 GBP` starts on the generic `General Expenses` path.
2. Accountant approves `Software & Cloud Services` plus the VAT/evidence/reconciliation rule.
3. Click **Approve & save to Sibyl Memory**.
4. Click **End Session A → Start Session B**. The page reloads.
5. **Session B:** synthetic `AWS EMEA SARL 240.00 GBP` arrives with no re-explanation.
6. Click **Ask Cherry in this fresh session** and inspect the recalled memory trace.
7. Click **Delete memory & run counterfactual** and observe the category revert to `General Expenses`.

All demo transactions are synthetic; this prototype is not tax or accounting advice.

## Tests

`tests/test_memory_acceptance.py` now exercises the real Sibyl client:

- creates Session A and persists an accountant decision
- discards Session A
- constructs a new gateway/client against the persisted Sibyl SQLite file
- recalls the rule in Session B
- verifies that the result changes to `Software & Cloud Services`
- runs the same transaction against an empty Sibyl DB and verifies the counterfactual `General Expenses` result
- verifies FTS5 recall for a related GitHub description when no supplier field is provided

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
├── app.py                         # FastAPI API + judge-facing demo UI
├── docs/
│   ├── architecture.md
│   └── demo-script.md
├── src/cherry_memory_ledger/
│   ├── __init__.py
│   ├── decision_engine.py         # memory/no-memory decision fork
│   ├── memory_gateway.py          # real Sibyl writes + reads
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

Cherry Money, its accounting/open-banking product direction, brand, and general accounting concepts pre-date this hackathon. The `cherry-memory-ledger` repository, Sibyl Memory adapter, fresh-session proof, browser-carried Sibyl SQLite demo transport, judge UI, tests and hackathon-specific implementation are work created during the Sibyl Labs build window.

Any pre-existing Cherry Money component reused later will be identified explicitly rather than presented as new hackathon work.

## Licence

MIT. See `LICENSE`.
