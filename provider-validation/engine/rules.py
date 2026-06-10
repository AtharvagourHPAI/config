"""R-001 .. R-010 as pure functions plus a registry indexed by change category.

Each rule has signature ``rule(change, contract, tags) -> RuleResult`` and is free
of side effects. A rule reports only *its own* verdict; cross-rule precedence is
resolved exclusively in ``decision_engine``. Failure outcomes are read from
``config/rules.yaml`` so verdicts can be retuned without editing this file.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from .config import load_rules_config
from .enums import ChangeCategory, Outcome, YesNo
from .models import ChangeRequest, ProviderContract, RuleResult, TagSet

RuleFn = Callable[[ChangeRequest, ProviderContract, TagSet], RuleResult]


def _failure_outcome(rule_id: str) -> Optional[Outcome]:
    meta = load_rules_config().get("rules", {}).get(rule_id, {})
    value = meta.get("failure_outcome")
    return Outcome(value) if value else None


def _result(rule_id: str, passed: bool, message: str) -> RuleResult:
    """Build a RuleResult, attaching the configured failure outcome when failed."""
    return RuleResult(
        rule_id=rule_id,
        passed=passed,
        verdict=None if passed else _failure_outcome(rule_id),
        message=message,
    )


# --------------------------------------------------------------------------- #
# Rule predicates
# --------------------------------------------------------------------------- #
def r001(change: ChangeRequest, contract: ProviderContract, tags: TagSet) -> RuleResult:
    """Correct CMS form: must be CMS-855I."""
    params = load_rules_config().get("parameters", {})
    accepted = params.get("accepted_cms_form", "CMS-855I")
    ok = change.cms_form == accepted
    return _result(
        "R-001",
        ok,
        f"Form is {change.cms_form}" if ok else f"Wrong form: {change.cms_form} (expected {accepted})",
    )


def r002(change: ChangeRequest, contract: ProviderContract, tags: TagSet) -> RuleResult:
    """Provider identifiers must match the source-of-truth contract."""
    ok = (change.provider_id is None) or (change.provider_id == contract.provider_id)
    return _result(
        "R-002",
        ok,
        "Identifiers match source-of-truth contract"
        if ok
        else f"Identifier mismatch: change {change.provider_id} vs contract {contract.provider_id}",
    )


def r003(change: ChangeRequest, contract: ProviderContract, tags: TagSet) -> RuleResult:
    """Out-of-state practice location add requires initial enrollment."""
    ok = not tags.cross_state_pl_add
    return _result(
        "R-003",
        ok,
        "Practice location add is in-state or not an add"
        if ok
        else f"Out-of-state practice location add ({change.new_location_state})",
    )


def r004(change: ChangeRequest, contract: ProviderContract, tags: TagSet) -> RuleResult:
    """Special payment address must be an allowed destination type."""
    ok = not tags.special_payment_invalid
    return _result(
        "R-004",
        ok,
        "Special payment address type is allowed"
        if ok
        else f"Disallowed special payment address: {change.requested_new_value!r}",
    )


def r005(change: ChangeRequest, contract: ProviderContract, tags: TagSet) -> RuleResult:
    """Final adverse legal action: exclusion/debarment/revocation is a hard block."""
    ok = not tags.exclusion_or_debarment
    return _result(
        "R-005",
        ok,
        "No exclusion/debarment finding"
        if ok
        else f"Exclusion/debarment finding: {change.requested_new_value!r}",
    )


def r006(change: ChangeRequest, contract: ProviderContract, tags: TagSet) -> RuleResult:
    """Reassignee must be an enrolled Medicare group/organization."""
    ok = not tags.reassignee_unverified
    return _result(
        "R-006",
        ok,
        "Reassignee enrollment verified"
        if ok
        else "Reassignee could not be verified as Medicare enrolled",
    )


def r007(change: ChangeRequest, contract: ProviderContract, tags: TagSet) -> RuleResult:
    """EFT change requires CMS-588 plus bank documentation."""
    ok = not tags.eft_docs_missing
    return _result(
        "R-007",
        ok,
        "EFT documentation present and verifiable"
        if ok
        else "Missing CMS-588 / voided check / bank letter",
    )


def r008(change: ChangeRequest, contract: ProviderContract, tags: TagSet) -> RuleResult:
    """Certification statement must be signed and dated."""
    ok = change.provider_signature_present == YesNo.YES
    return _result(
        "R-008",
        ok,
        "Certification statement signed"
        if ok
        else "Certification statement not signed",
    )


def r009(change: ChangeRequest, contract: ProviderContract, tags: TagSet) -> RuleResult:
    """Specialty change must be compatible with licensure / provider type."""
    ok = not tags.specialty_incompatible
    return _result(
        "R-009",
        ok,
        "Specialty change compatible with provider type"
        if ok
        else f"Incompatible provider-type reclassification: "
        f"{change.existing_value!r} -> {change.requested_new_value!r}",
    )


def r010(change: ChangeRequest, contract: ProviderContract, tags: TagSet) -> RuleResult:
    """Reuse existing documentation unless new evidence is required."""
    ok = tags.docs_complete
    return _result(
        "R-010",
        ok,
        "Documentation complete / reusable"
        if ok
        else "Additional documentation required before deciding",
    )


# --------------------------------------------------------------------------- #
# Registry: id -> (predicate, applicable category). "All" fires for every request.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class RegisteredRule:
    rule_id: str
    func: RuleFn
    applies_to: str  # "All" or a ChangeCategory value

    def applies(self, category: ChangeCategory) -> bool:
        return self.applies_to == "All" or self.applies_to == category.value


REGISTRY: dict[str, RegisteredRule] = {
    "R-001": RegisteredRule("R-001", r001, "All"),
    "R-002": RegisteredRule("R-002", r002, "All"),
    "R-003": RegisteredRule("R-003", r003, ChangeCategory.PRACTICE_LOCATION_ADDRESS.value),
    "R-004": RegisteredRule("R-004", r004, ChangeCategory.SPECIAL_PAYMENT_ADDRESS.value),
    "R-005": RegisteredRule("R-005", r005, ChangeCategory.FINAL_ADVERSE_LEGAL_ACTION.value),
    "R-006": RegisteredRule("R-006", r006, ChangeCategory.REASSIGNMENT.value),
    "R-007": RegisteredRule("R-007", r007, ChangeCategory.EFT_INFORMATION.value),
    "R-008": RegisteredRule("R-008", r008, "All"),
    "R-009": RegisteredRule("R-009", r009, ChangeCategory.PRIMARY_SPECIALTY.value),
    "R-010": RegisteredRule("R-010", r010, "All"),
}
