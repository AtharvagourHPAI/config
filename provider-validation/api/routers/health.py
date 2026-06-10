"""Liveness/readiness endpoint reporting the loaded reference counts."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import Store, get_store

router = APIRouter(tags=["health"])


@router.get("/health")
def health(store: Store = Depends(get_store)) -> dict:
    """Return ``ok`` plus how many contracts/changes/rules were loaded."""
    return {
        "status": "ok",
        "contracts": len(store.contracts),
        "changes": len(store.changes),
        "rules": len(store.rules),
    }
