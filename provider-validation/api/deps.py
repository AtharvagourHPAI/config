"""Startup data loading and the request-scoped store dependency.

The reference workbook is loaded exactly once (in the app lifespan) via
``engine.loaders.load_all`` and stashed on ``app.state``. Endpoints read it through
the ``get_store`` dependency. No business logic lives here — this is plumbing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import Request

from engine.loaders import (
    DEFAULT_CHANGES,
    DEFAULT_REFERENCE,
    load_all,
)
from engine.models import ChangeRequest, ProviderContract, RuleSpec

# Reference/input file names expected inside a custom ``DATA_PATH`` directory.
_REFERENCE_FILENAME = "reference_data.xlsx"
_CHANGES_FILENAME = "contract_change_requests.xlsx"


@dataclass
class Store:
    """The loaded reference data, indexed for O(1) lookups by the routers."""

    contracts: dict[str, ProviderContract]
    changes: list[ChangeRequest]
    rules: list[RuleSpec]
    changes_by_id: dict[str, ChangeRequest] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.changes_by_id:
            self.changes_by_id = {c.change_request_id: c for c in self.changes}


def _resolve_sources() -> tuple[object, object]:
    """Pick the reference/changes sources, honoring the ``DATA_PATH`` env var.

    ``DATA_PATH`` (if set) is a directory holding ``reference_data.xlsx`` and
    ``contract_change_requests.xlsx``. Unset → fall back to the engine defaults.
    """
    data_path = os.environ.get("DATA_PATH")
    if not data_path:
        return DEFAULT_REFERENCE, DEFAULT_CHANGES
    base = Path(data_path)
    return base / _REFERENCE_FILENAME, base / _CHANGES_FILENAME


def load_store() -> Store:
    """Load the workbook once into a :class:`Store` (called from the lifespan)."""
    reference_source, changes_source = _resolve_sources()
    bundle = load_all(reference_source, changes_source)
    return Store(
        contracts=bundle["contracts"],
        changes=bundle["changes"],
        rules=bundle["rules"],
    )


def get_store(request: Request) -> Store:
    """Dependency: return the process-wide store loaded at startup."""
    return request.app.state.store
