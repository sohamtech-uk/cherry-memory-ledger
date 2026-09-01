"""Acceptance-test scaffold for the load-bearing memory proof.

The test is skipped until real Sibyl persistence/recall is wired. Keeping the
scenario explicit prevents a weaker same-session cache from being mistaken
for the hackathon requirement.
"""

import pytest


@pytest.mark.skip(reason="Sibyl Memory integration not implemented yet")
def test_persist_fresh_session_recall_changes_decision() -> None:
    """Target end-to-end behaviour.

    Arrange / Session A
    -------------------
    1. Present a demo transaction such as `AMZN AWS EMEA`.
    2. Let the default decision path propose a generic category.
    3. Simulate an accountant correction to `Software & Cloud Services` with
       a scoped VAT/evidence rule.
    4. Persist that approved decision through `SibylMemoryGateway`.

    Fresh-session boundary
    ----------------------
    5. Terminate Session A completely. Do not reuse its Python objects,
       process memory, local cache, or chat context.
    6. Start Session B with a newly constructed gateway/client.

    Act / Session B
    ---------------
    7. Present a related but non-identical transaction such as `AWS EMEA SARL`.
    8. Recall the relevant accountant-approved memory from Sibyl.
    9. Feed the recalled memory into the decision path.

    Assert
    ------
    10. The outcome differs materially from the no-memory/default outcome.
    11. The result exposes which memory/rationale influenced it.
    12. If the new transaction violates the memory's reuse conditions, the
        decision becomes `review` rather than blindly copying the old rule.

    Counterfactual
    --------------
    13. With the memory unavailable/deleted, Session B must lose the learned
        treatment and fall back to the generic/default behaviour.
    """
    raise AssertionError("Replace this scaffold with the real acceptance test")
