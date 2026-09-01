# Demo script

Target length: **2–5 minutes**. The final recording should be one continuous segment for the fresh-session proof where practical, with an on-screen commit hash and/or timestamp so a judge can see that Session B is genuinely new.

This document is a recording plan, not a claim that the functionality already exists.

## 0:00–0:20 — Problem and promise

Show the repository/application and say, in substance:

> Accountants correct the same kinds of bookkeeping mistakes repeatedly because agent context disappears between sessions. Cherry Memory Ledger makes an approved accounting decision persist and influence a later, completely fresh session.

Show the current commit hash.

## 0:20–1:20 — Session A: teach the decision

Use synthetic data, for example:

```text
Transaction: AMZN AWS EMEA
Amount: £120.00
Default category: General Expenses
```

Have the demo accountant correct it to something like:

```text
Category: Software & Cloud Services
VAT treatment: reclaim only when the required qualifying VAT evidence is present
Scope: future AWS-related transactions for this demo business when the evidence condition matches
Rationale: accountant-approved supplier-specific treatment
```

Show the application persisting the decision through the real Sibyl integration. The final demo should expose enough evidence—logs/UI/trace—to make the write understandable without revealing secrets.

## 1:20–1:40 — Kill Session A

Make the boundary visible:

- stop/exit the application process or session;
- clear any intentionally non-persistent local/session state used by the prototype;
- start a new process/client/session;
- do not pass the old chat transcript or Python objects into Session B.

State explicitly that the only intended source of the learned decision is persistent Sibyl Memory.

## 1:40–2:40 — Session B: recall changes the outcome

Present a related but non-identical transaction, for example:

```text
Transaction: AWS EMEA SARL
Amount: £240.00
```

Show the new session recalling the earlier accountant-approved decision from Sibyl.

The result should visibly differ from the generic/no-memory path, for example:

```text
Category: Software & Cloud Services
Reason: matched prior accountant-approved AWS treatment
VAT: conditional on the remembered evidence requirement
Influencing memory: <memory id / human-readable reference>
```

This is the critical demo moment: **persist → fresh session → recall → changed decision**.

## 2:40–3:20 — Conflict / safe reuse

Present a transaction that looks similar but fails one remembered condition (for example, missing qualifying VAT evidence).

The desired behaviour is not blind copying. Cherry should preserve the remembered category where justified while changing the VAT/review outcome, or route the whole decision to human review depending on the implemented rules.

This demonstrates that memory contains context and scope, not just a supplier→category lookup table.

## 3:20–3:50 — Counterfactual

Disable/delete the relevant demo memory, or run an explicitly memory-unavailable path that is safe and easy to verify.

Show that the fresh session can no longer reproduce the learned accounting treatment and falls back to the generic/default path.

Only include this segment if the implementation makes the counterfactual clear and reliable.

## 3:50–4:20 — Architecture and code pointers

Briefly show:

- `SibylMemoryGateway.persist_accounting_decision(...)` — actual write implementation
- `SibylMemoryGateway.recall_relevant_decisions(...)` — actual read implementation
- the acceptance test proving a new process/session boundary
- any Sibyl primitives actually used

Do not tick or mention primitives that are not exercised by the code/demo.

## 4:20–4:40 — Partner integrations, only if real

If Base is genuinely implemented, show the executed on-chain action and transaction evidence. If Virtuals is genuinely implemented, show real agent coordination. Otherwise omit this section entirely rather than describing planned work as delivered functionality.

## Final submission checks

Before recording the final take:

- [ ] public repository points at the demoed commit;
- [ ] OSI-approved licence is present;
- [ ] Prior Work declaration is accurate;
- [ ] no secrets or private customer data appear on screen;
- [ ] fresh-session boundary is obvious;
- [ ] recalled memory is visible/traceable;
- [ ] recalled memory materially changes the decision;
- [ ] README code pointers match the actual implementation;
- [ ] only implemented memory primitives are declared;
- [ ] only exercised partner integrations are claimed;
- [ ] demo URL and public build posts are ready for the submission page.
