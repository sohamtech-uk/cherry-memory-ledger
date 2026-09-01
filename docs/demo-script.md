# Demo script

Target length: **2–5 minutes**. Record the critical fresh-session sequence as **one continuous, unedited segment**. The Session B result now renders both a UTC observation timestamp and the deployed Vercel commit SHA so the required proof is visible at the exact recall moment.

This plan describes the functionality currently implemented on `main` unless a section is explicitly marked as a stretch goal.

## 0:00–0:20 — Problem and promise

Open the deployed Cherry Memory Ledger application and say, in substance:

> Accountants correct the same kinds of bookkeeping mistakes repeatedly because agent context disappears between sessions. Cherry Memory Ledger makes an approved accounting decision persist and influence a later, genuinely fresh session.

Keep the recording continuous from here through the Session B recall.

## 0:20–1:20 — Session A: teach the decision

Use the pre-filled synthetic transaction:

```text
Transaction: AMZN AWS EMEA 120.00 GBP
Amount: £120.00
Default category: General Expenses
```

Point out Cherry's no-memory baseline, then show the accountant-approved correction:

```text
Category: Software & Cloud Services
VAT treatment: reclaim input VAT only when a valid VAT invoice is held
Reconciliation: match to monthly cloud-services invoice
Evidence: valid VAT invoice
```

Click **Approve & save to Sibyl Memory**.

Explain briefly that the application makes real Sibyl calls:

- `set_entity(...)` stores the current accountant-approved decision in the WARM entity tier;
- `write_event(...)` records the approval in the COLD journal.

The page should show a non-empty Sibyl memory snapshot and the logical rule id `demo-company:aws`.

## 1:20–1:40 — Fresh-session boundary

Click **End Session A → Start Session B**.

This intentionally reloads the page, destroying the page's JavaScript/session state. On the next request, the API creates a brand-new Sibyl `MemoryClient` from the persisted Sibyl SQLite bytes. No Session A Python object, chat transcript, or in-process cache is reused.

Keep this boundary and the following recall in the same unedited recording segment.

## 1:40–2:40 — Session B: recall changes the outcome

Session B contains a related but non-identical transaction:

```text
Transaction: AWS EMEA SARL 240.00 GBP
Amount: £240.00
```

Click **Ask Cherry in this fresh session**.

The expected result is:

```text
Source: Recalled from Sibyl Memory
Category: Software & Cloud Services
VAT: Reclaim input VAT only when a valid VAT invoice is held
Reconciliation: Match to monthly cloud-services invoice
Influencing memory: demo-company:aws
```

Point out the **Fresh-session proof** tile in the same result. It shows:

- the UTC time at which Session B produced the result; and
- the deployed Git commit SHA.

This is the critical judging beat: **persist → fresh session → recall → changed decision**, with the required on-screen timestamp/commit proof.

## 2:40–3:15 — Deletion counterfactual

Without changing the Session B transaction, click **Delete memory & run counterfactual**.

The expected result changes to:

```text
Source: No memory · default path
Category: General Expenses
```

Say explicitly:

> The transaction did not change. The only thing removed was Sibyl Memory. The learned accounting behaviour disappeared, which is why memory is load-bearing rather than decorative.

This is the cleanest visual evidence for the hackathon's deletion test.

## 3:15–3:55 — Code proof

Switch briefly to the public repository and show these exact locations:

- `src/cherry_memory_ledger/memory_gateway.py`
  - `SibylMemoryGateway.persist_accounting_decision(...)`
  - `SibylMemoryGateway.recall_relevant_decisions(...)`
- `src/cherry_memory_ledger/decision_engine.py`
  - the memory/no-memory decision fork
- `tests/test_memory_acceptance.py`
  - a new gateway/client is created for Session B
  - the Sibyl-backed result differs from an empty-memory counterfactual

Mention that GitHub Actions runs the acceptance suite on pushes and pull requests.

## 3:55–4:15 — Why the Vercel memory transport looks unusual

If useful, explain in one sentence:

> Sibyl is local-first and SQLite-backed; because Vercel functions have ephemeral filesystems, this hackathon demo checkpoints the real Sibyl SQLite file and carries those bytes in browser localStorage between stateless requests. The entity/journal/search operations are still Sibyl operations, not a replacement database.

Do not over-explain this in the video unless a judge would otherwise be confused.

## Stretch section — only if implemented before the final recording

Do **not** include any of the following unless they are genuinely exercised by the submitted build:

- Base executed on-chain action;
- Virtuals-native agent coordination;
- reflection/consolidation;
- true rule-version time travel;
- any search primitive beyond what the code actually implements.

If Base is added later, show the executed transaction/action, not merely a package import. If Virtuals is added later, show the actual ACP/agent coordination path.

## Final submission checks

Before recording the final take:

- [ ] production URL is on the commit you intend to submit;
- [ ] public repository is MIT licensed;
- [ ] fresh-session write → reload → recall is one continuous unedited segment;
- [ ] Session B result visibly shows UTC timestamp and deployed commit SHA;
- [ ] recalled memory materially changes the accounting decision;
- [ ] deletion counterfactual uses the same transaction and visibly loses the learned treatment;
- [ ] README points to real Sibyl writes and reads;
- [ ] Prior Work declaration is accurate;
- [ ] no secrets or private/customer accounting data are visible;
- [ ] only implemented memory primitives are selected on the submission page;
- [ ] only exercised partner integrations are claimed;
- [ ] demo video is 2–5 minutes;
- [ ] at least two public build posts are ready and tag `@sibylcap` plus any partner actually claimed.
