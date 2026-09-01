# Cherry Money product-base integration

Cherry Memory Ledger is not intended to replace the existing Cherry Money accounting application. The hackathon memory layer is being integrated **on top of the pre-existing private Cherry Money product**.

## Repository boundary

### Private prior-work product: `sohamtech-uk/cherrymoney`

Cherry Money already provides the application and accounting workflows, including:

- Laravel authentication and company tenancy
- Open Banking / Finexer transaction ingestion
- `OpenBankingTransaction`
- invoices and expenses
- `SmartBankMatcher` reconciliation suggestions
- chart of accounts / `LedgerAccount`
- `BankLedgerPostingService` double-entry posting
- existing bank Transactions workbench

These capabilities pre-date the Sibyl Labs hackathon and are **Prior Work**. They are not presented as new hackathon functionality.

### Public hackathon repo: `sohamtech-uk/cherry-memory-ledger`

This public repository contains the new memory capability and the reproducible evidence judges need:

- official Sibyl Memory client integration
- structured accountant-decision memory model
- `set_entity` and `write_event` persistence
- `get_entity` / FTS5 recall
- fresh-session acceptance tests
- no-memory counterfactual
- public Vercel demo and judging proof

## Real Cherry Money composition

The private Cherry Money hackathon branch composes the two systems as follows:

```text
Open Banking / CSV bank transaction
              |
              v
Existing Cherry Money SmartBankMatcher
              |
              | generic baseline suggestion
              v
     Cherry Memory Ledger bridge
          /               \
         / recall           \ remember
        v                     v
public Sibyl service    accountant posts to
(cherry-memory-ledger)  existing LedgerAccount
        |                     |
        +----------+----------+
                   v
      enriched Cherry suggestion
                   |
                   v
existing BankLedgerPostingService
                   |
                   v
          Cherry Money ledger
```

The accounting application remains authoritative. Sibyl does not move money and does not independently post journals.

## Write path

1. Cherry Money loads an existing bank debit.
2. The existing `SmartBankMatcher` produces the ordinary heuristic suggestion.
3. A human accountant selects the actual Cherry Money ledger account.
4. The existing `BankLedgerPostingService` posts the transaction.
5. When **Remember with Sibyl** is selected, the accountant-approved allocation and scope are sent to this public memory service.
6. The service writes the decision to Sibyl and returns the updated local-first SQLite snapshot.
7. The private Cherry Money application encrypts that opaque snapshot using Laravel application encryption and stores it on the company record.

A memory-service failure does **not** roll back a successful accounting posting.

## Fresh-session recall path

1. A later Cherry Money request receives another related bank debit.
2. Cherry Money calculates its normal `SmartBankMatcher` baseline first.
3. The company’s encrypted Sibyl snapshot is decrypted server-side.
4. The snapshot is sent to this stateless public service.
5. A newly constructed Sibyl client recalls the accountant-approved decision.
6. When a memory matches, Cherry shows the remembered allocation and provenance alongside/in place of the generic heuristic.
7. The existing Cherry Money posting workflow remains responsible for any accounting action.

## Load-bearing counterfactual

Removing Sibyl does **not** make the pre-existing Cherry Money application disappear. It specifically breaks the new hackathon capability:

> **company-specific accountant decisions no longer survive into later fresh sessions.**

Without memory, the same bank transaction falls back to the ordinary Cherry Money matcher. With memory, it can use the accountant-approved allocation, rationale and reconciliation rule.

That learned behaviour is the load-bearing product capability being judged.

## Why keep this repository public?

The commercial Cherry Money codebase is private. Judges still need a public repository with an OSI-approved licence, transparent Sibyl calls, reproducible fresh-session tests and a working demo. This repository provides that evidence without publishing unrelated proprietary application code or credentials.

## Public demo vs product integration

The public Vercel demo carries the Sibyl SQLite snapshot in browser `localStorage` solely because Vercel functions have ephemeral filesystems and the demo must be independently reproducible.

The Cherry Money integration does **not** use browser storage for accounting memory. It stores the returned snapshot encrypted with the company inside Cherry Money’s database and decrypts it server-side only for memory calls.

## Partner stacks

Base and Virtuals remain stretch goals. Neither is claimed until a real integration is implemented and exercised in the demo.
