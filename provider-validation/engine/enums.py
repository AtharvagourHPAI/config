"""Controlled vocabularies for the validation engine.

All enums are plain ``str`` enums so they serialize cleanly and compare to raw
sheet values without surprises. Membership is intentionally closed: loaders coerce
raw strings into these enums and will raise on anything unexpected, which keeps the
decision path deterministic.
"""

from __future__ import annotations

from enum import Enum


class Outcome(str, Enum):
    """The five valid validation outcomes (the controlled vocabulary in ``Lists``)."""

    APPROVE = "APPROVE"
    DEVELOP = "DEVELOP"
    DENY = "DENY"
    REJECT = "REJECT"
    INITIAL_ENROLLMENT_REQUIRED = "INITIAL_ENROLLMENT_REQUIRED"


class ChangeAction(str, Enum):
    """What the change request does to a field on the contract."""

    ADD = "Add"
    CHANGE = "Change"
    TERMINATE = "Terminate"


class ChangeCategory(str, Enum):
    """The kind of contract attribute a change request targets.

    These mirror the distinct ``change_category`` values present in the dataset.
    """

    PRACTICE_LOCATION_ADDRESS = "Practice Location Address"
    CORRESPONDENCE_ADDRESS = "Correspondence Address"
    SPECIAL_PAYMENT_ADDRESS = "Special Payment Address"
    PRIMARY_SPECIALTY = "Primary Specialty"
    BILLING_AGENCY = "Billing Agency"
    FINAL_ADVERSE_LEGAL_ACTION = "Final Adverse Legal Action"
    MANAGING_EMPLOYEE = "Managing Employee"
    EFT_INFORMATION = "EFT Information"
    VOLUNTARY_TERMINATION = "Voluntary Termination"
    BUSINESS_STRUCTURE = "Business Structure"
    REASSIGNMENT = "Reassignment"


class ContractStatus(str, Enum):
    """Lifecycle state of an existing provider contract."""

    ACTIVE = "Active"
    SUSPENDED = "Suspended"


class YesNo(str, Enum):
    """Tri-state flag used across the change request sheet (``Yes``/``No``/``N/A``)."""

    YES = "Yes"
    NO = "No"
    NA = "N/A"


class ScreeningTier(str, Enum):
    """Screening intensity required for a change request."""

    MED_SAM = "MED/SAM check"
    MED_SAM_ADVERSE = "MED/SAM + adverse action review"
