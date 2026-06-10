"""Decision endpoints — thin wrappers over ``engine.decision_engine.decide``.

A business denial (DENY/REJECT/...) is a *successful* evaluation and returns 200.
4xx is reserved for transport problems: 404 unknown id, 422 invalid body.
"""

from __future__ import annotations

import io
from typing import Optional

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile

from engine.decision_engine import decide
from engine.loaders import IntegrityError, _assert_integrity, load_changes
from engine.scoring import score_all

from ..deps import Store, get_store
from ..schemas import (
    BatchItem,
    BatchRequest,
    BatchResponse,
    DecisionByIdRequest,
    DecisionInlineRequest,
    DecisionResponse,
    UploadDecisionItem,
    UploadDistribution,
    UploadResponse,
)

router = APIRouter(prefix="/v1/decisions", tags=["decisions"])


def _decide_by_id(store: Store, change_request_id: str):
    """Resolve a change + its contract from the store and decide. 404 if missing."""
    change = store.changes_by_id.get(change_request_id)
    if change is None:
        raise HTTPException(
            status_code=404, detail=f"Unknown change_request_id: {change_request_id}"
        )
    contract = store.contracts.get(change.linked_provider_contract_id)
    if contract is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Linked contract not found: {change.linked_provider_contract_id}"
            ),
        )
    return decide(change, contract)


@router.post("/by-id", response_model=DecisionResponse)
def decide_by_id(
    body: DecisionByIdRequest,
    store: Store = Depends(get_store),
    x_correlation_id: Optional[str] = Header(default=None),
) -> DecisionResponse:
    decision = _decide_by_id(store, body.change_request_id)
    return DecisionResponse(decision=decision, correlation_id=x_correlation_id)


@router.post("/inline", response_model=DecisionResponse)
def decide_inline(
    body: DecisionInlineRequest,
    x_correlation_id: Optional[str] = Header(default=None),
) -> DecisionResponse:
    decision = decide(body.change, body.contract)
    return DecisionResponse(decision=decision, correlation_id=x_correlation_id)


@router.post("/batch", response_model=BatchResponse)
def decide_batch(
    body: BatchRequest,
    store: Store = Depends(get_store),
    x_correlation_id: Optional[str] = Header(default=None),
) -> BatchResponse:
    results: list[BatchItem] = []
    for change_request_id in body.change_request_ids:
        change = store.changes_by_id.get(change_request_id)
        if change is None:
            results.append(
                BatchItem(
                    change_request_id=change_request_id,
                    found=False,
                    error=f"Unknown change_request_id: {change_request_id}",
                )
            )
            continue
        contract = store.contracts.get(change.linked_provider_contract_id)
        if contract is None:
            results.append(
                BatchItem(
                    change_request_id=change_request_id,
                    found=False,
                    error=(
                        "Linked contract not found: "
                        f"{change.linked_provider_contract_id}"
                    ),
                )
            )
            continue
        results.append(
            BatchItem(
                change_request_id=change_request_id,
                found=True,
                decision=decide(change, contract),
            )
        )
    return BatchResponse(correlation_id=x_correlation_id, results=results)


@router.post("/upload", response_model=UploadResponse)
async def decide_upload(
    file: UploadFile = File(...),
    store: Store = Depends(get_store),
    x_correlation_id: Optional[str] = Header(default=None),
) -> UploadResponse:
    """Score an uploaded change-request workbook — HTTP parity with the UI.

    Mirrors the Streamlit upload+process flow: parse the ``Requested_Contract_Changes``
    sheet, integrity-check it against the reference contracts loaded at startup, then
    decide every row. A malformed file or broken referential integrity is a transport
    error (422); successful scoring — including business denials — returns 200.
    """
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    try:
        changes = load_changes(io.BytesIO(raw))
        _assert_integrity(store.contracts, changes)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=422, detail=f"Referential integrity failed: {exc}"
        )
    except Exception as exc:  # malformed workbook, wrong/missing sheet, etc.
        raise HTTPException(
            status_code=422,
            detail=(
                "Could not read the input file. Make sure it is an .xlsx with a "
                f"'Requested_Contract_Changes' sheet. Details: {exc}"
            ),
        )

    bundle = {
        "contracts": store.contracts,
        "rules": store.rules,
        "changes": changes,
    }
    report = score_all(data=bundle)
    decisions = report["decisions"]

    results = [
        UploadDecisionItem(
            change_request_id=change.change_request_id,
            decision=decisions[change.change_request_id],
        )
        for change in changes
    ]

    return UploadResponse(
        correlation_id=x_correlation_id,
        filename=file.filename or "upload.xlsx",
        total_changes=len(changes),
        labeled=report["total"],
        correct=report["correct"],
        accuracy=report["accuracy"],
        distribution=UploadDistribution(
            expected=report["distribution"]["expected"],
            actual=report["distribution"]["actual"],
        ),
        per_category=report["per_category"],
        results=results,
    )
