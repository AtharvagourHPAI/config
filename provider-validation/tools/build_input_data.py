"""Organize the raw workbook into the two files the engine consumes.

The original ``provider_contract_change_request_datasets.xlsx`` bundles everything
in one book. For the reviewer workflow we split it into two purpose-built files:

* ``data/reference_data.xlsx`` — the static, source-of-truth REFERENCE:
  ``Existing_Provider_Contracts``, ``Validation_Rules``, ``Lists``, ``Summary``.
  This ships with the app and rarely changes.

* ``data/contract_change_requests.xlsx`` — the INPUT a reviewer uploads:
  the ``Requested_Contract_Changes`` sheet. We also append extra dummy rows so
  there is a fuller spread of DENY, DEVELOP, and REJECT ("review") outcomes to
  look at (REJECT is absent from the original labeled data).

Re-run any time the source workbook changes:

    python tools/build_input_data.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
SOURCE = DATA / "provider_contract_change_request_datasets.xlsx"
REFERENCE_OUT = DATA / "reference_data.xlsx"
CHANGES_OUT = DATA / "contract_change_requests.xlsx"

SHEET_CONTRACTS = "Existing_Provider_Contracts"
SHEET_CHANGES = "Requested_Contract_Changes"
SHEET_RULES = "Validation_Rules"
SHEET_SUMMARY = "Summary"
SHEET_LISTS = "Lists"

REFERENCE_SHEETS = [SHEET_CONTRACTS, SHEET_RULES, SHEET_SUMMARY, SHEET_LISTS]

SOT_RULE = "Manual/Application based CMS-855I change-of-information validation"
CERT = "CMS-855I Certification Statement signed"


def _deny_adverse(cr: str, pc: str, prv: str) -> dict:
    """Final adverse legal action (exclusion/debarment) -> DENY via R-005."""
    return {
        "change_request_id": cr,
        "linked_provider_contract_id": pc,
        "provider_id": prv,
        "request_date": "2026-08-15",
        "requested_effective_date": "2026-08-25",
        "change_category": "Final Adverse Legal Action",
        "change_action": "Add",
        "cms_form": "CMS-855I",
        "requesting_party_role": "Individual Practitioner",
        "provider_signature_present": "Yes",
        "contact_person_present": "Yes",
        "existing_value": "No adverse action on file",
        "requested_new_value": "Undisclosed OIG exclusion/debarment hit",
        "new_location_state": "N/A",
        "new_location_same_state": "N/A",
        "supporting_docs_submitted": CERT,
        "development_requested": "No",
        "development_response_due_date": None,
        "screening_required": "MED/SAM + adverse action review",
        "source_of_truth_rule": SOT_RULE,
        "expected_validation_outcome": "DENY",
        "expected_contract_action": "Do not update contract; initiate denial/revocation review",
        "validation_notes": "Exclusion/debarment finding blocks approval (synthetic review sample).",
        "old_contract_snapshot_key": f"{pc}-CURRENT",
        "new_contract_snapshot_key": f"{pc}-POSTCHANGE",
    }


def _deny_specialty(cr: str, pc: str, prv: str) -> dict:
    """Incompatible provider-type reclassification -> DENY via R-009."""
    return {
        "change_request_id": cr,
        "linked_provider_contract_id": pc,
        "provider_id": prv,
        "request_date": "2026-08-15",
        "requested_effective_date": "2026-08-25",
        "change_category": "Primary Specialty",
        "change_action": "Change",
        "cms_form": "CMS-855I",
        "requesting_party_role": "Individual Practitioner",
        "provider_signature_present": "Yes",
        "contact_person_present": "Yes",
        "existing_value": "Internal Medicine",
        "requested_new_value": "Physician Assistant",
        "new_location_state": "N/A",
        "new_location_same_state": "N/A",
        "supporting_docs_submitted": CERT,
        "development_requested": "No",
        "development_response_due_date": None,
        "screening_required": "MED/SAM check",
        "source_of_truth_rule": SOT_RULE,
        "expected_validation_outcome": "DENY",
        "expected_contract_action": "Do not update specialty; provider type eligibility/licensure mismatch",
        "validation_notes": "Specialty change incompatible with provider type/licensure (synthetic review sample).",
        "old_contract_snapshot_key": f"{pc}-CURRENT",
        "new_contract_snapshot_key": f"{pc}-POSTCHANGE",
    }


def _develop_reassignment(cr: str, pc: str, prv: str) -> dict:
    """Unverified reassignee -> DEVELOP via R-006."""
    return {
        "change_request_id": cr,
        "linked_provider_contract_id": pc,
        "provider_id": prv,
        "request_date": "2026-08-16",
        "requested_effective_date": "2026-08-28",
        "change_category": "Reassignment",
        "change_action": "Add",
        "cms_form": "CMS-855I",
        "requesting_party_role": "Individual Practitioner",
        "provider_signature_present": "Yes",
        "contact_person_present": "Yes",
        "existing_value": "Clear",
        "requested_new_value": "Reassign benefits to group GC-7700 / NPI 2400000077",
        "new_location_state": "N/A",
        "new_location_same_state": "N/A",
        "supporting_docs_submitted": f"{CERT}; Section 4F reassignment details",
        "development_requested": "Yes",
        "development_response_due_date": "2026-09-15",
        "screening_required": "MED/SAM check",
        "source_of_truth_rule": SOT_RULE,
        "expected_validation_outcome": "DEVELOP",
        "expected_contract_action": "Hold until reassignee enrollment is verified",
        "validation_notes": "Requested reassignee could not be verified as Medicare enrolled (synthetic review sample).",
        "old_contract_snapshot_key": f"{pc}-CURRENT",
        "new_contract_snapshot_key": f"{pc}-POSTCHANGE",
    }


def _develop_eft(cr: str, pc: str, prv: str) -> dict:
    """Missing EFT documentation -> DEVELOP via R-007."""
    return {
        "change_request_id": cr,
        "linked_provider_contract_id": pc,
        "provider_id": prv,
        "request_date": "2026-08-17",
        "requested_effective_date": "2026-08-29",
        "change_category": "EFT Information",
        "change_action": "Change",
        "cms_form": "CMS-855I",
        "requesting_party_role": "Individual Practitioner",
        "provider_signature_present": "Yes",
        "contact_person_present": "No",
        "existing_value": "EFT account ending 2044",
        "requested_new_value": "New routing/account token EFT-9044",
        "new_location_state": "N/A",
        "new_location_same_state": "N/A",
        "supporting_docs_submitted": "CMS-588 EFT Authorization Agreement; CMS-855I signed certification",
        "development_requested": "Yes",
        "development_response_due_date": "2026-09-16",
        "screening_required": "MED/SAM check",
        "source_of_truth_rule": SOT_RULE,
        "expected_validation_outcome": "DEVELOP",
        "expected_contract_action": "Hold pending bank documentation",
        "validation_notes": "Missing voided check or bank letter; develop pending documentation (synthetic review sample).",
        "old_contract_snapshot_key": f"{pc}-CURRENT",
        "new_contract_snapshot_key": f"{pc}-POSTCHANGE",
    }


def _develop_special_payment(cr: str, pc: str, prv: str) -> dict:
    """Disallowed special payment address -> DEVELOP via R-004."""
    return {
        "change_request_id": cr,
        "linked_provider_contract_id": pc,
        "provider_id": prv,
        "request_date": "2026-08-18",
        "requested_effective_date": "2026-08-30",
        "change_category": "Special Payment Address",
        "change_action": "Change",
        "cms_form": "CMS-855I",
        "requesting_party_role": "Individual Practitioner",
        "provider_signature_present": "Yes",
        "contact_person_present": "Yes",
        "existing_value": "Practice Location",
        "requested_new_value": "Private residence address",
        "new_location_state": "N/A",
        "new_location_same_state": "N/A",
        "supporting_docs_submitted": CERT,
        "development_requested": "Yes",
        "development_response_due_date": "2026-09-17",
        "screening_required": "MED/SAM check",
        "source_of_truth_rule": SOT_RULE,
        "expected_validation_outcome": "DEVELOP",
        "expected_contract_action": "Hold change request pending acceptable special payment address evidence",
        "validation_notes": "Special payment address must be an allowed type (synthetic review sample).",
        "old_contract_snapshot_key": f"{pc}-CURRENT",
        "new_contract_snapshot_key": f"{pc}-POSTCHANGE",
    }


def _develop_adverse_disclosure(cr: str, pc: str, prv: str) -> dict:
    """Non-exclusion adverse disclosure under development -> DEVELOP via R-010."""
    return {
        "change_request_id": cr,
        "linked_provider_contract_id": pc,
        "provider_id": prv,
        "request_date": "2026-08-19",
        "requested_effective_date": "2026-08-31",
        "change_category": "Final Adverse Legal Action",
        "change_action": "Add",
        "cms_form": "CMS-855I",
        "requesting_party_role": "Individual Practitioner",
        "provider_signature_present": "Yes",
        "contact_person_present": "Yes",
        "existing_value": "No adverse action on file",
        "requested_new_value": "New state license probation disclosure",
        "new_location_state": "N/A",
        "new_location_same_state": "N/A",
        "supporting_docs_submitted": CERT,
        "development_requested": "Yes",
        "development_response_due_date": "2026-09-18",
        "screening_required": "MED/SAM + adverse action review",
        "source_of_truth_rule": SOT_RULE,
        "expected_validation_outcome": "DEVELOP",
        "expected_contract_action": "Hold pending adverse action documentation",
        "validation_notes": "Adverse disclosure (non-exclusion) developed pending documentation (synthetic review sample).",
        "old_contract_snapshot_key": f"{pc}-CURRENT",
        "new_contract_snapshot_key": f"{pc}-POSTCHANGE",
    }


def _reject_wrong_form(cr: str, pc: str, prv: str) -> dict:
    """Submission on the wrong CMS form -> REJECT via R-001."""
    return {
        "change_request_id": cr,
        "linked_provider_contract_id": pc,
        "provider_id": prv,
        "request_date": "2026-08-20",
        "requested_effective_date": "2026-09-01",
        "change_category": "Correspondence Address",
        "change_action": "Change",
        "cms_form": "CMS-855O",
        "requesting_party_role": "Individual Practitioner",
        "provider_signature_present": "Yes",
        "contact_person_present": "Yes",
        "existing_value": "123 Old Correspondence Ave",
        "requested_new_value": "456 New Correspondence Blvd",
        "new_location_state": "N/A",
        "new_location_same_state": "N/A",
        "supporting_docs_submitted": "CMS-855O submission (wrong form)",
        "development_requested": "No",
        "development_response_due_date": None,
        "screening_required": "MED/SAM check",
        "source_of_truth_rule": SOT_RULE,
        "expected_validation_outcome": "REJECT",
        "expected_contract_action": "Return submission to provider; resubmit on CMS-855I",
        "validation_notes": "Wrong CMS form for a CMS-855I practitioner; procedurally invalid (synthetic reject sample).",
        "old_contract_snapshot_key": f"{pc}-CURRENT",
        "new_contract_snapshot_key": f"{pc}-POSTCHANGE",
    }


def _reject_missing_signature(cr: str, pc: str, prv: str) -> dict:
    """Submission missing the certification signature -> REJECT via R-008."""
    return {
        "change_request_id": cr,
        "linked_provider_contract_id": pc,
        "provider_id": prv,
        "request_date": "2026-08-21",
        "requested_effective_date": "2026-09-02",
        "change_category": "Correspondence Address",
        "change_action": "Change",
        "cms_form": "CMS-855I",
        "requesting_party_role": "Individual Practitioner",
        "provider_signature_present": "No",
        "contact_person_present": "Yes",
        "existing_value": "789 Prior Mailing Rd",
        "requested_new_value": "1010 Updated Mailing Way",
        "new_location_state": "N/A",
        "new_location_same_state": "N/A",
        "supporting_docs_submitted": "Change form submitted without signed certification statement",
        "development_requested": "No",
        "development_response_due_date": None,
        "screening_required": "MED/SAM check",
        "source_of_truth_rule": SOT_RULE,
        "expected_validation_outcome": "REJECT",
        "expected_contract_action": "Return submission to provider; obtain signed certification statement",
        "validation_notes": "Certification statement not signed; procedurally invalid (synthetic reject sample).",
        "old_contract_snapshot_key": f"{pc}-CURRENT",
        "new_contract_snapshot_key": f"{pc}-POSTCHANGE",
    }


def dummy_rows() -> list[dict]:
    """Deterministic extra change requests: 6 DENY + 6 DEVELOP + 2 REJECT ("review")."""
    return [
        _deny_adverse("CR-2026-00061", "PC-2026-00003", "PRV-10003"),
        _deny_adverse("CR-2026-00062", "PC-2026-00007", "PRV-10007"),
        _deny_adverse("CR-2026-00063", "PC-2026-00012", "PRV-10012"),
        _deny_adverse("CR-2026-00064", "PC-2026-00018", "PRV-10018"),
        _deny_specialty("CR-2026-00065", "PC-2026-00022", "PRV-10022"),
        _deny_specialty("CR-2026-00066", "PC-2026-00025", "PRV-10025"),
        _develop_reassignment("CR-2026-00067", "PC-2026-00030", "PRV-10030"),
        _develop_reassignment("CR-2026-00068", "PC-2026-00033", "PRV-10033"),
        _develop_eft("CR-2026-00069", "PC-2026-00036", "PRV-10036"),
        _develop_eft("CR-2026-00070", "PC-2026-00039", "PRV-10039"),
        _develop_special_payment("CR-2026-00071", "PC-2026-00042", "PRV-10042"),
        _develop_adverse_disclosure("CR-2026-00072", "PC-2026-00045", "PRV-10045"),
        _reject_wrong_form("CR-2026-00073", "PC-2026-00048", "PRV-10048"),
        _reject_missing_signature("CR-2026-00074", "PC-2026-00050", "PRV-10050"),
    ]


def build() -> None:
    book = pd.ExcelFile(SOURCE)

    # --- Reference file (source of truth) ---
    with pd.ExcelWriter(REFERENCE_OUT, engine="openpyxl") as writer:
        for sheet in REFERENCE_SHEETS:
            if sheet in book.sheet_names:
                df = pd.read_excel(
                    SOURCE, sheet_name=sheet, dtype=object, keep_default_na=False
                )
                df.to_excel(writer, sheet_name=sheet, index=False)

    # --- Input file (uploaded change requests) + dummy review rows ---
    changes = pd.read_excel(
        SOURCE, sheet_name=SHEET_CHANGES, dtype=object, keep_default_na=False
    )
    extra = pd.DataFrame(dummy_rows())[list(changes.columns)]
    combined = pd.concat([changes, extra], ignore_index=True)
    with pd.ExcelWriter(CHANGES_OUT, engine="openpyxl") as writer:
        combined.to_excel(writer, sheet_name=SHEET_CHANGES, index=False)

    contracts = pd.read_excel(
        SOURCE, sheet_name=SHEET_CONTRACTS, dtype=object, keep_default_na=False
    )
    print(f"Wrote {REFERENCE_OUT.name}: {len(contracts)} contracts + rules/lists/summary")
    print(
        f"Wrote {CHANGES_OUT.name}: {len(combined)} change requests "
        f"({len(changes)} original + {len(extra)} dummy review rows)"
    )
    print(combined["expected_validation_outcome"].value_counts().to_string())


if __name__ == "__main__":
    build()
