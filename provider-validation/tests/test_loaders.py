"""Loader integrity tests: counts, zero orphans, in-vocabulary labels."""

from __future__ import annotations

import pytest

from engine.enums import Outcome
from engine.loaders import IntegrityError, _assert_integrity, load_all


@pytest.fixture(scope="module")
def bundle():
    return load_all()


def test_counts(bundle):
    assert len(bundle["contracts"]) == 80
    # 60 original change requests + 14 appended dummy DENY/DEVELOP/REJECT review rows.
    assert len(bundle["changes"]) == 74
    assert len(bundle["rules"]) == 10


def test_zero_orphans(bundle):
    contract_ids = set(bundle["contracts"])
    orphans = [
        c.change_request_id
        for c in bundle["changes"]
        if c.linked_provider_contract_id not in contract_ids
    ]
    assert orphans == []


def test_labels_in_vocabulary(bundle):
    valid = set(Outcome)
    for change in bundle["changes"]:
        assert change.expected_validation_outcome in valid


def test_rule_ids(bundle):
    ids = {r.rule_id for r in bundle["rules"]}
    assert ids == {f"R-{i:03d}" for i in range(1, 11)}


def test_integrity_raises_on_orphan(bundle):
    changes = list(bundle["changes"])
    changes[0].linked_provider_contract_id = "PC-DOES-NOT-EXIST"
    with pytest.raises(IntegrityError):
        _assert_integrity(bundle["contracts"], changes)
