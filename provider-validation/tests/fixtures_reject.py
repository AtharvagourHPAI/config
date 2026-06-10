"""Synthetic fixtures and builders for cases absent from the labeled data.

``REJECT`` never appears in the workbook (0 rows), so it cannot be regression-tested
from labels — it must be exercised with hand-built procedural-failure cases here.
These builders are also reused by the rule/decision unit tests.
"""

from __future__ import annotations

from typing import Any

from engine.enums import ChangeAction, ChangeCategory, ContractStatus, ScreeningTier, YesNo
from engine.models import ChangeRequest, ProviderContract

CONTRACT_DEFAULTS: dict[str, Any] = {
    "provider_contract_id": "PC-TEST-0001",
    "provider_id": "PRV-TEST-1",
    "npi": "1999999999",
    "ptan": "P999999",
    "tax_id_or_ssn_key": "99-9999999",
    "legal_business_name": "Test Clinic LLC",
    "individual_name": "Dr. Test Provider",
    "provider_type": "Individual Practitioner",
    "primary_specialty": "Internal Medicine",
    "contract_status": ContractStatus.ACTIVE,
    "pecos_enrollment_status": "Approved",
    "business_structure": "LLC",
    "practice_state": "TX",
    "sanction_screening_status": "Clear",
}

CHANGE_DEFAULTS: dict[str, Any] = {
    "change_request_id": "CR-TEST-0001",
    "linked_provider_contract_id": "PC-TEST-0001",
    "provider_id": "PRV-TEST-1",
    "change_category": ChangeCategory.CORRESPONDENCE_ADDRESS,
    "change_action": ChangeAction.CHANGE,
    "cms_form": "CMS-855I",
    "provider_signature_present": YesNo.YES,
    "new_location_same_state": YesNo.NA,
    "development_requested": YesNo.NO,
    "screening_required": ScreeningTier.MED_SAM,
}


def make_contract(**overrides: Any) -> ProviderContract:
    """Build a valid baseline contract, with field overrides."""
    return ProviderContract(**{**CONTRACT_DEFAULTS, **overrides})


def make_change(**overrides: Any) -> ChangeRequest:
    """Build a clean (would-APPROVE) change request, with field overrides."""
    return ChangeRequest(**{**CHANGE_DEFAULTS, **overrides})


def reject_wrong_form() -> tuple[ChangeRequest, ProviderContract]:
    """A submission on the wrong CMS form -> REJECT (R-001)."""
    return make_change(cms_form="CMS-855O"), make_contract()


def reject_missing_signature() -> tuple[ChangeRequest, ProviderContract]:
    """A submission missing the certification signature -> REJECT (R-008)."""
    return make_change(provider_signature_present=YesNo.NO), make_contract()
