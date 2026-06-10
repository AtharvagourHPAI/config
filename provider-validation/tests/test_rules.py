"""Unit tests for each rule R-001..R-010 with a passing and a failing input."""

from __future__ import annotations

from engine import rules
from engine.enums import ChangeAction, ChangeCategory, Outcome, YesNo
from engine.tag_engine import derive
from tests.fixtures_reject import make_change, make_contract


def _run(rule_fn, change, contract):
    tags = derive(change, contract)
    return rule_fn(change, contract, tags)


def test_r001_form():
    assert _run(rules.r001, make_change(), make_contract()).passed
    res = _run(rules.r001, make_change(cms_form="CMS-855O"), make_contract())
    assert not res.passed and res.verdict == Outcome.REJECT


def test_r002_identifiers():
    assert _run(rules.r002, make_change(), make_contract()).passed
    res = _run(rules.r002, make_change(provider_id="PRV-OTHER"), make_contract())
    assert not res.passed and res.verdict == Outcome.DEVELOP


def test_r003_cross_state_practice_location_add():
    ok = make_change(
        change_category=ChangeCategory.PRACTICE_LOCATION_ADDRESS,
        change_action=ChangeAction.ADD,
        new_location_same_state=YesNo.YES,
    )
    assert _run(rules.r003, ok, make_contract()).passed
    bad = make_change(
        change_category=ChangeCategory.PRACTICE_LOCATION_ADDRESS,
        change_action=ChangeAction.ADD,
        new_location_same_state=YesNo.NO,
        new_location_state="CA",
    )
    res = _run(rules.r003, bad, make_contract())
    assert not res.passed and res.verdict == Outcome.INITIAL_ENROLLMENT_REQUIRED


def test_r004_special_payment_address():
    ok = make_change(
        change_category=ChangeCategory.SPECIAL_PAYMENT_ADDRESS,
        requested_new_value="P.O. Box 443",
    )
    assert _run(rules.r004, ok, make_contract()).passed
    bad = make_change(
        change_category=ChangeCategory.SPECIAL_PAYMENT_ADDRESS,
        requested_new_value="Private residence address",
    )
    res = _run(rules.r004, bad, make_contract())
    assert not res.passed and res.verdict == Outcome.DEVELOP


def test_r005_adverse_exclusion():
    ok = make_change(
        change_category=ChangeCategory.FINAL_ADVERSE_LEGAL_ACTION,
        requested_new_value="New state license probation disclosure",
    )
    assert _run(rules.r005, ok, make_contract()).passed
    bad = make_change(
        change_category=ChangeCategory.FINAL_ADVERSE_LEGAL_ACTION,
        requested_new_value="Undisclosed OIG exclusion hit",
    )
    res = _run(rules.r005, bad, make_contract())
    assert not res.passed and res.verdict == Outcome.DENY


def test_r006_reassignee_unverified():
    ok = make_change(
        change_category=ChangeCategory.REASSIGNMENT, development_requested=YesNo.NO
    )
    assert _run(rules.r006, ok, make_contract()).passed
    bad = make_change(
        change_category=ChangeCategory.REASSIGNMENT, development_requested=YesNo.YES
    )
    res = _run(rules.r006, bad, make_contract())
    assert not res.passed and res.verdict == Outcome.DEVELOP


def test_r007_eft_docs():
    ok = make_change(
        change_category=ChangeCategory.EFT_INFORMATION, development_requested=YesNo.NO
    )
    assert _run(rules.r007, ok, make_contract()).passed
    bad = make_change(
        change_category=ChangeCategory.EFT_INFORMATION, development_requested=YesNo.YES
    )
    res = _run(rules.r007, bad, make_contract())
    assert not res.passed and res.verdict == Outcome.DEVELOP


def test_r008_signature():
    assert _run(rules.r008, make_change(), make_contract()).passed
    res = _run(rules.r008, make_change(provider_signature_present=YesNo.NO), make_contract())
    assert not res.passed and res.verdict == Outcome.REJECT


def test_r009_specialty_compatibility():
    ok = make_change(
        change_category=ChangeCategory.PRIMARY_SPECIALTY,
        existing_value="Internal Medicine",
        requested_new_value="Cardiology",
    )
    assert _run(rules.r009, ok, make_contract()).passed
    bad = make_change(
        change_category=ChangeCategory.PRIMARY_SPECIALTY,
        existing_value="Internal Medicine",
        requested_new_value="Physician Assistant",
    )
    res = _run(rules.r009, bad, make_contract())
    assert not res.passed and res.verdict == Outcome.DENY


def test_r010_documentation_reuse():
    assert _run(rules.r010, make_change(development_requested=YesNo.NO), make_contract()).passed
    res = _run(rules.r010, make_change(development_requested=YesNo.YES), make_contract())
    assert not res.passed and res.verdict == Outcome.DEVELOP
