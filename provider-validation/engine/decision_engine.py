"""The decision engine: the ONLY place rule precedence lives.

``decide`` derives tags, evaluates the applicable rules, then walks an ordered
precedence ladder (first match wins, stop). The ladder is intentionally explicit
so the resolution of competing verdicts is auditable.
"""

from __future__ import annotations

from .config import default_contract_action
from .enums import Outcome
from .models import ChangeRequest, Decision, ProviderContract, RuleResult, TagSet
from .rule_engine import evaluate
from .tag_engine import derive

# DEVELOP-class rules, in the order their failure should be reported as the winner.
_DEVELOP_RULES = ("R-002", "R-004", "R-006", "R-007", "R-010")


def _failed(results: dict[str, RuleResult], rule_id: str) -> bool:
    res = results.get(rule_id)
    return res is not None and not res.passed


def _resolve(
    tags: TagSet, results: dict[str, RuleResult]
) -> tuple[Outcome, str | None, str]:
    """Apply the precedence ladder. Returns (outcome, winning_rule, explanation)."""

    # Tier 1 — substantive hard blocks -> DENY.
    if tags.exclusion_or_debarment:
        return Outcome.DENY, "R-005", "Final adverse legal action (exclusion/debarment) blocks approval."
    if tags.specialty_incompatible:
        return Outcome.DENY, "R-009", "Specialty change is incompatible with provider type/licensure."

    # Tier 2 — procedural invalidity -> REJECT.
    if _failed(results, "R-001"):
        return Outcome.REJECT, "R-001", "Submission uses the wrong CMS form."
    if _failed(results, "R-008"):
        return Outcome.REJECT, "R-008", "Certification statement is not signed."

    # Tier 3 — cannot be processed as a modification -> INITIAL_ENROLLMENT_REQUIRED.
    if tags.cross_state_pl_add:
        return (
            Outcome.INITIAL_ENROLLMENT_REQUIRED,
            "R-003",
            "Out-of-state practice location add requires a separate initial enrollment.",
        )

    # Tier 4 — needs more information / documentation -> DEVELOP.
    for rule_id in _DEVELOP_RULES:
        if _failed(results, rule_id):
            return (
                Outcome.DEVELOP,
                rule_id,
                f"{rule_id} requires additional information before a decision.",
            )
    if not tags.docs_complete:
        return Outcome.DEVELOP, "R-010", "Additional documentation required before deciding."

    # Tier 5 — default.
    return Outcome.APPROVE, None, "All applicable rules passed."


def decide(change: ChangeRequest, contract: ProviderContract) -> Decision:
    """Return the deterministic, explainable decision for one change request.

    Never reads the ground-truth label fields on ``change``.
    """
    tags = derive(change, contract)
    evaluated = evaluate(change, contract, tags)
    results = {r.rule_id: r for r in evaluated}

    outcome, winning_rule, reason = _resolve(tags, results)
    action = default_contract_action(outcome.value)

    fired = tags.fired()
    fired_str = ", ".join(fired) if fired else "none"
    explanation = f"{outcome.value} — {reason} Winning rule: {winning_rule or 'none'}. Tags fired: {fired_str}."

    return Decision(
        change_request_id=change.change_request_id,
        outcome=outcome,
        contract_action=action,
        evaluated_rules=evaluated,
        tags=tags,
        winning_rule=winning_rule,
        explanation=explanation,
    )
