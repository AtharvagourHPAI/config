"""Request/response WRAPPERS around the engine's Pydantic models.

These never redefine the engine models — they nest them. The ``Decision`` portion of
every response is a faithful serialization of the engine object (no decision fields
added or removed); any transport-level metadata (e.g. ``correlation_id``) lives
*outside* the Decision so determinism is preserved.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from engine.models import ChangeRequest, Decision, ProviderContract

OutcomeCounts = dict[str, int]

# Ground-truth label fields that must never be exposed over the API.
LABEL_FIELDS = ("expected_validation_outcome", "expected_contract_action")


class DecisionByIdRequest(BaseModel):
    """Resolve a change request (and its linked contract) from the loaded store."""

    change_request_id: str


class DecisionInlineRequest(BaseModel):
    """Caller supplies both objects; the engine models are reused as-is."""

    change: ChangeRequest
    contract: ProviderContract


class BatchRequest(BaseModel):
    """Score many known change requests in one call, preserving input order."""

    change_request_ids: list[str]


class DecisionResponse(BaseModel):
    """A faithful Decision plus optional transport-level correlation id."""

    decision: Decision
    correlation_id: Optional[str] = None


class BatchItem(BaseModel):
    """One per-id result. Unknown ids are reported here, not as a batch failure."""

    change_request_id: str
    found: bool
    decision: Optional[Decision] = None
    error: Optional[str] = None


class BatchResponse(BaseModel):
    """Ordered batch results plus optional transport-level correlation id."""

    correlation_id: Optional[str] = None
    results: list[BatchItem]


class UploadDecisionItem(BaseModel):
    """One scored change request from an uploaded workbook (input order)."""

    change_request_id: str
    decision: Decision


class UploadDistribution(BaseModel):
    """Expected (label) vs. actual (engine) outcome counts for the upload."""

    expected: OutcomeCounts
    actual: OutcomeCounts


class UploadResponse(BaseModel):
    """Mirror of the Streamlit upload+process workflow over HTTP.

    Scores every row of an uploaded ``Requested_Contract_Changes`` workbook against
    the reference contracts/rulebook loaded at startup. ``labeled``/``correct``/
    ``accuracy`` are computed only over rows carrying a ground-truth label.
    """

    correlation_id: Optional[str] = None
    filename: str
    total_changes: int
    labeled: int
    correct: int
    accuracy: float
    distribution: UploadDistribution
    per_category: dict[str, float]
    results: list[UploadDecisionItem]


def change_public_dict(change: ChangeRequest) -> dict:
    """Serialize a change request with the ground-truth label fields stripped."""
    return change.model_dump(mode="json", exclude=set(LABEL_FIELDS))
