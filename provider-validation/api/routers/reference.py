"""Read-back endpoints for contracts, change requests, and the rulebook.

Change requests are returned with their ground-truth label fields stripped — those
remain test-only and must never leave the engine boundary.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from engine.config import load_rules_config

from ..deps import Store, get_store
from ..schemas import change_public_dict

router = APIRouter(prefix="/v1", tags=["reference"])


@router.get("/contracts/{contract_id}")
def get_contract(contract_id: str, store: Store = Depends(get_store)) -> dict:
    contract = store.contracts.get(contract_id)
    if contract is None:
        raise HTTPException(
            status_code=404, detail=f"Unknown provider_contract_id: {contract_id}"
        )
    return contract.model_dump(mode="json")


@router.get("/changes/{change_request_id}")
def get_change(change_request_id: str, store: Store = Depends(get_store)) -> dict:
    change = store.changes_by_id.get(change_request_id)
    if change is None:
        raise HTTPException(
            status_code=404, detail=f"Unknown change_request_id: {change_request_id}"
        )
    return change_public_dict(change)


@router.get("/rules")
def get_rules() -> dict:
    """Return the editable rulebook straight from ``config/rules.yaml``."""
    return load_rules_config()
