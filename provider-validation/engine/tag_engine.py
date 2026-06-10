"""Tag engine: derive boolean/enum signals from a (change, contract) pair.

``derive`` is a pure function with no side effects and no I/O beyond reading the
cached rulebook parameters. The same inputs always yield the same ``TagSet``.
"""

from __future__ import annotations

from .config import rule_params
from .enums import ChangeAction, ChangeCategory, ContractStatus, ScreeningTier, YesNo
from .models import ChangeRequest, ProviderContract, TagSet


def _contains_any(text: str | None, needles: list[str]) -> bool:
    if not text:
        return False
    low = text.lower()
    return any(n.lower() in low for n in needles)


def derive(change: ChangeRequest, contract: ProviderContract) -> TagSet:
    """Compute the full ``TagSet`` for one change request against its contract."""
    params = rule_params()

    cross_state = change.new_location_same_state == YesNo.NO
    same_state = change.new_location_same_state == YesNo.YES

    adverse = change.change_category == ChangeCategory.FINAL_ADVERSE_LEGAL_ACTION
    exclusion = adverse and _contains_any(
        change.requested_new_value, params.get("exclusion_keywords", [])
    )

    needs_development = change.development_requested == YesNo.YES

    # Reassignee verification and EFT documentation completeness are operational
    # facts the contractor confirms off-system; in this dataset that confirmation
    # gap is surfaced as `development_requested = Yes` for the affected category.
    reassignee_unverified = (
        change.change_category == ChangeCategory.REASSIGNMENT and needs_development
    )
    eft_docs_missing = (
        change.change_category == ChangeCategory.EFT_INFORMATION and needs_development
    )

    special_payment_invalid = (
        change.change_category == ChangeCategory.SPECIAL_PAYMENT_ADDRESS
        and not _contains_any(
            change.requested_new_value, params.get("special_payment_allowed_types", [])
        )
    )

    specialty_incompatible = (
        change.change_category == ChangeCategory.PRIMARY_SPECIALTY
        and change.requested_new_value in params.get("incompatible_specialty_targets", [])
    )

    cross_state_pl_add = (
        change.change_category == ChangeCategory.PRACTICE_LOCATION_ADDRESS
        and change.change_action == ChangeAction.ADD
        and cross_state
    )

    return TagSet(
        same_state=same_state,
        cross_state=cross_state,
        signature_present=change.provider_signature_present == YesNo.YES,
        docs_complete=not needs_development,
        adverse_action_flag=adverse,
        reassignee_unverified=reassignee_unverified,
        contract_suspended=contract.contract_status == ContractStatus.SUSPENDED,
        eft_docs_missing=eft_docs_missing,
        screening_tier=change.screening_required,
        exclusion_or_debarment=exclusion,
        specialty_incompatible=specialty_incompatible,
        special_payment_invalid=special_payment_invalid,
        cross_state_pl_add=cross_state_pl_add,
        needs_development=needs_development,
    )
