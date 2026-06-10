"""Pydantic v2 data models for the validation engine.

These typed models are the boundary between messy spreadsheet rows and the pure,
deterministic decision core. Coercing raw cells into these models is also where
controlled-vocabulary enforcement happens (an out-of-vocabulary enum value raises).
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from .enums import (
    ChangeAction,
    ChangeCategory,
    ContractStatus,
    Outcome,
    ScreeningTier,
    YesNo,
)


class ProviderContract(BaseModel):
    """Source-of-truth state of an already-enrolled CMS-855I provider contract.

    Maps all 43 columns of ``Existing_Provider_Contracts``. Decision-relevant fields
    are typed precisely; the long tail is ``Optional`` and rarely read by rules.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    provider_contract_id: str
    provider_id: Optional[str] = None
    npi: Optional[str] = None
    ptan: Optional[str] = None
    individual_name: Optional[str] = None
    provider_type: Optional[str] = None
    primary_specialty: Optional[str] = None
    secondary_specialty: Optional[str] = None
    contract_status: Optional[ContractStatus] = None
    pecos_enrollment_status: Optional[str] = None
    medicare_enrollment_form: Optional[str] = None
    tax_id_or_ssn_key: Optional[str] = None
    legal_business_name: Optional[str] = None
    business_structure: Optional[str] = None
    current_practice_location_name: Optional[str] = None
    practice_address_line1: Optional[str] = None
    practice_city: Optional[str] = None
    practice_state: Optional[str] = None
    practice_zip4: Optional[str] = None
    correspondence_same_as_practice: Optional[str] = None
    correspondence_address: Optional[str] = None
    special_payment_address_type: Optional[str] = None
    accepting_new_patients: Optional[str] = None
    license_number: Optional[str] = None
    license_state: Optional[str] = None
    license_effective_date: Optional[Any] = None
    license_expiration_date: Optional[Any] = None
    dea_required: Optional[str] = None
    dea_registration_status: Optional[str] = None
    final_adverse_action_on_file: Optional[str] = None
    sanction_screening_status: Optional[str] = None
    reassignment_status: Optional[str] = None
    reassigned_group_contract_id: Optional[str] = None
    reassigned_group_npi: Optional[str] = None
    billing_agency_on_file: Optional[str] = None
    eft_on_file: Optional[str] = None
    contract_effective_date: Optional[Any] = None
    contract_end_date: Optional[Any] = None
    last_revalidation_date: Optional[Any] = None
    next_revalidation_due: Optional[Any] = None
    source_of_truth_system: Optional[str] = None
    source_rule_reference: Optional[str] = None
    record_confidence: Optional[str] = None

    # Convenience alias used by some rules / UI.
    @property
    def tin(self) -> Optional[str]:
        return self.tax_id_or_ssn_key


class ChangeRequest(BaseModel):
    """An inbound request to change an existing contract.

    Maps all 25 columns of ``Requested_Contract_Changes``. ``expected_validation_outcome``
    and ``expected_contract_action`` are ground-truth labels used ONLY by tests/scoring;
    ``decide()`` must never read them.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    change_request_id: str
    linked_provider_contract_id: str
    provider_id: Optional[str] = None
    request_date: Optional[Any] = None
    requested_effective_date: Optional[Any] = None
    change_category: ChangeCategory
    change_action: ChangeAction
    cms_form: str
    requesting_party_role: Optional[str] = None
    provider_signature_present: YesNo
    contact_person_present: Optional[str] = None
    existing_value: Optional[str] = None
    requested_new_value: Optional[str] = None
    new_location_state: Optional[str] = None
    new_location_same_state: YesNo
    supporting_docs_submitted: Optional[str] = None
    development_requested: YesNo
    development_response_due_date: Optional[Any] = None
    screening_required: Optional[ScreeningTier] = None
    source_of_truth_rule: Optional[str] = None
    # --- ground-truth labels (tests/scoring only) ---
    expected_validation_outcome: Optional[Outcome] = None
    expected_contract_action: Optional[str] = None
    validation_notes: Optional[str] = None
    old_contract_snapshot_key: Optional[str] = None
    new_contract_snapshot_key: Optional[str] = None


class RuleSpec(BaseModel):
    """Editable metadata for a single rule, loaded from the workbook and config."""

    rule_id: str
    validation_rule: str
    manual_or_application_basis: Optional[str] = None
    applies_to_change_category: str = "All"
    expected_action_when_failed: Optional[str] = None
    # Outcome produced when this rule fails (sourced from config/rules.yaml).
    failure_outcome: Optional[Outcome] = None


class TagSet(BaseModel):
    """Derived, boolean/enum signals computed once per (change, contract) pair.

    The prompt's required tags plus a few explicit, decision-relevant refinements
    (``exclusion_or_debarment``, ``specialty_incompatible``, ``special_payment_invalid``,
    ``cross_state_pl_add``, ``needs_development``) that the labeled data requires.
    """

    same_state: bool = False
    cross_state: bool = False
    signature_present: bool = False
    docs_complete: bool = True
    adverse_action_flag: bool = False
    reassignee_unverified: bool = False
    contract_suspended: bool = False
    eft_docs_missing: bool = False
    screening_tier: Optional[ScreeningTier] = None
    # --- refinements driven by the labeled dataset ---
    exclusion_or_debarment: bool = False
    specialty_incompatible: bool = False
    special_payment_invalid: bool = False
    cross_state_pl_add: bool = False
    needs_development: bool = False

    def fired(self) -> list[str]:
        """Return the names of the boolean tags that are True (for display/trace)."""
        names = [
            "same_state",
            "cross_state",
            "signature_present",
            "adverse_action_flag",
            "reassignee_unverified",
            "contract_suspended",
            "eft_docs_missing",
            "exclusion_or_debarment",
            "specialty_incompatible",
            "special_payment_invalid",
            "cross_state_pl_add",
            "needs_development",
        ]
        out = [n for n in names if getattr(self, n)]
        if not self.docs_complete:
            out.append("docs_incomplete")
        return out


class RuleResult(BaseModel):
    """Outcome of evaluating one rule against one change request."""

    rule_id: str
    passed: bool
    verdict: Optional[Outcome] = None
    message: str = ""


class Decision(BaseModel):
    """The full, explainable result of ``decide(change, contract)``."""

    change_request_id: Optional[str] = None
    outcome: Outcome
    contract_action: str
    evaluated_rules: list[RuleResult] = []
    tags: TagSet
    winning_rule: Optional[str] = None
    explanation: str = ""
