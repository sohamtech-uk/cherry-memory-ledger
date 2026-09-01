# Cherry Memory Ledger

**Accounting decisions that compound, instead of disappearing.**

Cherry Memory Ledger is a Sibyl Labs hackathon prototype for an accounting agent that can carry accountant-approved corrections, VAT treatments, reconciliation decisions, and business-specific rules into genuinely fresh sessions.

The core hypothesis is simple: a correction should not disappear when a chat or process ends. A later transaction should be handled differently because the agent remembers what the accountant previously approved.

## Hackathon objective

Build and demonstrate this load-bearing memory loop:

1. An accountant corrects or approves an accounting decision.
2. The decision, context, rationale, and scope are persisted to Sibyl Memory.
3. The original session/process is ended.
4. A genuinely fresh session receives a new but related transaction.
5. The agent recalls the relevant approved memory without the user re-entering it.
6. The recalled memory changes the categorisation, VAT treatment, reconciliation action, or review decision.

If memory is deleted or disabled, the prototype must lose that learned accounting behaviour and revert to a generic/default decision path. That counterfactual is intentional: Sibyl Memory is meant to be on the critical path, not an optional profile feature.

## What breaks when memory is deleted?

Without Sibyl Memory, Cherry loses the accountant-approved corrections, VAT treatments and reconciliation decisions that determine how future transactions are processed. Fresh sessions therefore revert to generic guesses, repeat previously corrected mistakes, and cannot consistently apply the business's approved accounting treatment.

## Fresh-session acceptance criteria

The first end-to-end milestone is complete only when all of the following are demonstrable:

- **Persist:** Session A stores an accountant-approved correction with enough context to reuse it safely.
- **Fresh session:** Session A is terminated and Session B starts without carrying in-memory application state from Session A.
- **Recall:** Session B retrieves the relevant prior decision from Sibyl Memory for a new transaction.
- **Changed decision:** the recalled decision materially changes the outcome versus the no-memory/default path.
- **Traceability:** the demo can show which memory influenced the decision and why.
- **Conflict handling:** where the new transaction does not safely match the remembered rule, the agent flags it for review rather than blindly applying it.

Target walkthrough text for the eventual submission form:

> **Persist:** Accountant-approved transaction corrections, VAT treatments, supplier-specific reconciliation rules and the context/rationale behind each decision.  
> **Recall (fresh session):** When a new transaction arrives, Cherry retrieves relevant approved history for that supplier or a semantically similar transaction without the user re-explaining it.  
> **Changes the agent's decision by:** Cherry applies the remembered accounting/VAT treatment when the remembered scope matches, or flags a conflict for human review instead of repeating the previous mistake.

## Memory model

The prototype is designed to remember decisions, not just free-text notes. A memory record is expected to carry fields such as:

- business identifier (demo-safe / non-sensitive)
- supplier or counterparty entity
- transaction fingerprint and description
- original proposed treatment
- accountant-approved treatment
- VAT treatment and evidence requirements
- reconciliation mapping/action
- rationale
- approval role and timestamp
- scope/conditions for reuse
- confidence/review status
- supersedes/superseded-by metadata for rule evolution

See `src/cherry_memory_ledger/models.py` for the initial domain model.

## Sibyl Memory integration status

**Status: scaffold only — live Sibyl reads/writes are not implemented yet.**

The intended integration boundary is deliberately explicit so judges and reviewers can find the memory path easily:

- Planned memory write: `src/cherry_memory_ledger/memory_gateway.py` → `SibylMemoryGateway.persist_accounting_decision(...)`
- Planned memory read: `src/cherry_memory_ledger/memory_gateway.py` → `SibylMemoryGateway.recall_relevant_decisions(...)`

Those methods currently fail loudly with `NotImplementedError`. They will only be replaced once the Sibyl Memory client/API shape has been validated during the hackathon. We will not claim a primitive or integration until it exists in code and is exercised in the demo.

### Planned Sibyl primitives

Initial targets, subject to implementation and verification:

- recall
- entities
- semantic search
- temporal / time-travel for superseded accounting rules
- reflection for turning corrections into reusable candidate rules

Only primitives actually implemented and demonstrated will be declared in the final submission.

## Partner stacks

Partner integrations are stretch goals after the core Sibyl loop works.

### Base — planned, not implemented

Potential use: anchor a cryptographic fingerprint of an accountant-approved decision or audit event on Base while keeping the detailed accounting context in Sibyl Memory. This repository does **not** currently contain an on-chain action and will not claim the Base multiplier unless an actual transaction is implemented and demonstrated.

### Virtuals Protocol — planned, not implemented

Potential use: coordinate a bookkeeping agent and an accounting-review agent around memory-backed exceptions. This repository does **not** currently contain a Virtuals integration and will not claim it unless real runtime coordination is implemented and demonstrated.

## Prior Work declaration

Cherry Money, its accounting/open-banking product direction, brand, and general accounting concepts pre-date this hackathon. The `cherry-memory-ledger` repository, the Sibyl Memory integration, the fresh-session memory proof, and hackathon-specific implementation in this repository are intended to be work created during the Sibyl Labs build window.

Where any pre-existing Cherry Money component is later reused, it will be identified clearly in the README and/or pull request rather than presented as new hackathon work.

## Repository layout

```text
.
├── docs/
│   ├── architecture.md
│   └── demo-script.md
├── src/cherry_memory_ledger/
│   ├── __init__.py
│   ├── memory_gateway.py
│   └── models.py
├── tests/
│   └── test_memory_acceptance.py
├── .gitignore
├── LICENSE
├── pyproject.toml
└── README.md
```

## Local setup

Python 3.11+ is the initial target.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

Sibyl's hackathon setup flow currently starts with the CLI/MCP package:

```bash
pip install 'sibyl-memory-cli[mcp]'
sibyl init
sibyl setup
sibyl status
```

The application integration will be added only after the client/API contract is confirmed.

## Tests

The acceptance-test file is intentionally a skipped scaffold today. It documents the exact behaviour the first functional implementation must satisfy:

```bash
pytest
```

No passing Sibyl integration test is claimed yet.

## Demo target

The demo will centre on one visible behaviour:

1. Session A misclassifies a demo AWS transaction.
2. An accountant corrects it and approves a scoped VAT treatment.
3. The correction is persisted.
4. Session A is fully terminated.
5. Session B starts fresh with a related AWS transaction.
6. Cherry recalls the prior approved decision and changes its outcome.
7. A no-memory/counterfactual path shows that the learned behaviour disappears when memory is unavailable.

See `docs/demo-script.md` for the recording plan.

## Licence

MIT. See `LICENSE`.
