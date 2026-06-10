"""Decision-engine precedence tests, including the synthetic REJECT cases."""

from __future__ import annotations

from engine.decision_engine import decide
from engine.enums import ChangeAction, ChangeCategory, Outcome, YesNo
from tests.fixtures_reject import (
    make_change,
    make_contract,
    reject_missing_signature,
    reject_wrong_form,
)


def test_clean_change_approves():
    d = decide(make_change(), make_contract())
    assert d.outcome == Outcome.APPROVE
    assert d.winning_rule is None


def test_reject_wrong_form():
    change, contract = reject_wrong_form()
    d = decide(change, contract)
    assert d.outcome == Outcome.REJECT
    assert d.winning_rule == "R-001"


def test_reject_missing_signature():
    change, contract = reject_missing_signature()
    d = decide(change, contract)
    assert d.outcome == Outcome.REJECT
    assert d.winning_rule == "R-008"


def test_precedence_adverse_beats_reject():
    """Adverse exclusion AND a missing signature -> DENY (tier 1 beats tier 2)."""
    change = make_change(
        change_category=ChangeCategory.FINAL_ADVERSE_LEGAL_ACTION,
        requested_new_value="Undisclosed OIG exclusion hit",
        provider_signature_present=YesNo.NO,  # would otherwise REJECT
    )
    d = decide(change, make_contract())
    assert d.outcome == Outcome.DENY
    assert d.winning_rule == "R-005"


def test_cross_state_practice_location_add_initial_enrollment():
    change = make_change(
        change_category=ChangeCategory.PRACTICE_LOCATION_ADDRESS,
        change_action=ChangeAction.ADD,
        new_location_same_state=YesNo.NO,
        new_location_state="CA",
    )
    d = decide(change, make_contract())
    assert d.outcome == Outcome.INITIAL_ENROLLMENT_REQUIRED
    assert d.winning_rule == "R-003"


def test_specialty_incompatible_denies():
    change = make_change(
        change_category=ChangeCategory.PRIMARY_SPECIALTY,
        existing_value="Internal Medicine",
        requested_new_value="Physician Assistant",
    )
    d = decide(change, make_contract())
    assert d.outcome == Outcome.DENY
    assert d.winning_rule == "R-009"


def test_development_request_develops():
    change = make_change(
        change_category=ChangeCategory.EFT_INFORMATION,
        development_requested=YesNo.YES,
    )
    d = decide(change, make_contract())
    assert d.outcome == Outcome.DEVELOP


def test_decide_ignores_label_fields():
    """decide() must not be influenced by the ground-truth label on the request."""
    change = make_change(expected_validation_outcome=Outcome.DENY)
    d = decide(change, make_contract())
    assert d.outcome == Outcome.APPROVE


def test_trace_is_populated():
    d = decide(make_change(), make_contract())
    assert d.evaluated_rules  # at least the All-category rules fired
    assert d.explanation
    assert d.contract_action
