"""Batch scorer: run ``decide`` over every change request and compare to labels.

The label fields are read *here* (in scoring/tests) only — never inside the
decision path.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from .decision_engine import decide
from .enums import Outcome
from .loaders import DEFAULT_CHANGES, DEFAULT_REFERENCE, ExcelSource, load_all
from .models import ChangeRequest, Decision, ProviderContract


def score_all(
    reference_source: ExcelSource = DEFAULT_REFERENCE,
    changes_source: ExcelSource = DEFAULT_CHANGES,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Decide every change request and report accuracy against ground truth.

    Pass an already-loaded ``data`` bundle to score an uploaded input file without
    re-reading from disk. Returns a dict with: ``total``, ``correct``, ``accuracy``,
    ``confusion`` (``{(expected, predicted): count}``), ``per_category`` accuracy,
    expected vs. actual ``distribution``, the ``mismatches`` (with full traces), and
    every ``decision`` keyed by change_request_id.
    """
    bundle = data or load_all(reference_source, changes_source)
    contracts: dict[str, ProviderContract] = bundle["contracts"]
    changes: list[ChangeRequest] = bundle["changes"]

    correct = 0
    confusion: Counter[tuple[str, str]] = Counter()
    cat_total: Counter[str] = Counter()
    cat_correct: Counter[str] = Counter()
    expected_dist: Counter[str] = Counter()
    predicted_dist: Counter[str] = Counter()
    mismatches: list[dict[str, Any]] = []
    decisions: dict[str, Decision] = {}

    for change in changes:
        contract = contracts[change.linked_provider_contract_id]
        decision = decide(change, contract)
        decisions[change.change_request_id] = decision

        predicted = decision.outcome.value
        expected = (
            change.expected_validation_outcome.value
            if change.expected_validation_outcome
            else None
        )
        predicted_dist[predicted] += 1
        cat = change.change_category.value

        if expected is not None:
            expected_dist[expected] += 1
            confusion[(expected, predicted)] += 1
            cat_total[cat] += 1
            is_match = expected == predicted
            if is_match:
                correct += 1
                cat_correct[cat] += 1
            else:
                mismatches.append(
                    {
                        "change_request_id": change.change_request_id,
                        "change_category": cat,
                        "expected": expected,
                        "predicted": predicted,
                        "expected_action": change.expected_contract_action,
                        "predicted_action": decision.contract_action,
                        "winning_rule": decision.winning_rule,
                        "explanation": decision.explanation,
                        "decision": decision,
                    }
                )

    total = sum(expected_dist.values())
    per_category = {
        cat: cat_correct[cat] / cat_total[cat] for cat in sorted(cat_total)
    }

    return {
        "total": total,
        "correct": correct,
        "accuracy": (correct / total) if total else 0.0,
        "confusion": dict(confusion),
        "per_category": per_category,
        "distribution": {
            "expected": dict(expected_dist),
            "actual": dict(predicted_dist),
        },
        "mismatches": mismatches,
        "decisions": decisions,
    }


def outcome_distribution(report: dict[str, Any]) -> dict[str, int]:
    """Predicted distribution padded to include all five outcomes (zeros included)."""
    actual = report["distribution"]["actual"]
    return {o.value: actual.get(o.value, 0) for o in Outcome}
