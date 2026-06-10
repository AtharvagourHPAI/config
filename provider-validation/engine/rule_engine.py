"""Evaluate the applicable subset of rules for a single change request.

Only rules whose ``applies_to`` matches the change category (or ``All``) fire, in
deterministic ascending rule-id order.
"""

from __future__ import annotations

from .models import ChangeRequest, ProviderContract, RuleResult, TagSet
from .rules import REGISTRY


def evaluate(
    change: ChangeRequest, contract: ProviderContract, tags: TagSet
) -> list[RuleResult]:
    """Run every applicable rule and return their results in rule-id order."""
    results: list[RuleResult] = []
    for rule_id in sorted(REGISTRY):
        rule = REGISTRY[rule_id]
        if rule.applies(change.change_category):
            results.append(rule.func(change, contract, tags))
    return results
