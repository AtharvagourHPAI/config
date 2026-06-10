"""Full regression: reproduce all 60 labels and the expected distribution.

Also asserts the acceptance criteria that tie outcomes to specific rules.
"""

from __future__ import annotations

import pytest

from engine.enums import Outcome
from engine.loaders import load_all
from engine.scoring import score_all


@pytest.fixture(scope="module")
def report():
    return score_all()


@pytest.fixture(scope="module")
def changes_by_id():
    return {c.change_request_id: c for c in load_all()["changes"]}


def test_all_labels_reproduced(report):
    # 60 original labels + 14 appended dummy DENY/DEVELOP/REJECT review rows.
    assert report["total"] == 74
    assert report["correct"] == 74
    assert report["accuracy"] == 1.0
    assert report["mismatches"] == []


def test_expected_distribution(report):
    actual = report["distribution"]["actual"]
    assert actual.get("APPROVE") == 49
    assert actual.get("DEVELOP") == 12
    assert actual.get("DENY") == 10
    assert actual.get("INITIAL_ENROLLMENT_REQUIRED") == 1
    # REJECT is absent from the original labeled data; the 2 here are synthetic
    # review rows (wrong form via R-001, missing signature via R-008).
    assert actual.get("REJECT", 0) == 2


def test_initial_enrollment_traces_to_r003(report):
    initials = [
        d for d in report["decisions"].values()
        if d.outcome == Outcome.INITIAL_ENROLLMENT_REQUIRED
    ]
    assert len(initials) == 1
    assert initials[0].winning_rule == "R-003"


def test_denies_trace_to_adverse_or_specialty(report):
    denies = [d for d in report["decisions"].values() if d.outcome == Outcome.DENY]
    assert len(denies) == 10
    # Every DENY is an adverse-exclusion (R-005) or incompatible-specialty (R-009).
    winners = {d.winning_rule for d in denies}
    assert winners <= {"R-005", "R-009"}
    assert sum(d.winning_rule == "R-005" for d in denies) == 7
    assert sum(d.winning_rule == "R-009" for d in denies) == 3


def test_rejects_trace_to_form_or_signature(report):
    rejects = [d for d in report["decisions"].values() if d.outcome == Outcome.REJECT]
    assert len(rejects) == 2
    # Every REJECT is a wrong-form (R-001) or unsigned-certification (R-008) case.
    winners = {d.winning_rule for d in rejects}
    assert winners <= {"R-001", "R-008"}
    assert sum(d.winning_rule == "R-001" for d in rejects) == 1
    assert sum(d.winning_rule == "R-008" for d in rejects) == 1


def test_develops_correlate_with_development_requested(report, changes_by_id):
    for cid, d in report["decisions"].items():
        if d.outcome == Outcome.DEVELOP:
            change = changes_by_id[cid]
            assert (
                change.development_requested.value == "Yes"
                or change.development_response_due_date is not None
            )
