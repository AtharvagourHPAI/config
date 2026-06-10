"""Workbook -> typed models, with referential-integrity and vocabulary asserts.

The loader is the single place raw spreadsheet rows are coerced into Pydantic
models. It enforces the two data invariants the rest of the system relies on:
zero orphan change-request links, and every label inside the controlled vocabulary.

The input data is organized into two files (see ``tools/build_input_data.py``):

* ``reference_data.xlsx`` — the source-of-truth REFERENCE (existing contracts,
  the rulebook, and the controlled-vocabulary lists). Ships with the app.
* ``contract_change_requests.xlsx`` — the INPUT a reviewer uploads. Change
  requests can also be supplied as a file-like object (e.g. a Streamlit upload).
"""

from __future__ import annotations

from pathlib import Path
from typing import IO, Any, Union

import pandas as pd

from .config import load_rules_config
from .enums import Outcome
from .models import ChangeRequest, ProviderContract, RuleSpec

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# The static reference (contracts + rulebook + lists) and the uploadable input.
DEFAULT_REFERENCE = DATA_DIR / "reference_data.xlsx"
DEFAULT_CHANGES = DATA_DIR / "contract_change_requests.xlsx"

# Back-compat alias: the original single workbook still contains every sheet, so
# callers passing it explicitly keep working.
DEFAULT_WORKBOOK = DATA_DIR / "provider_contract_change_request_datasets.xlsx"

# A spreadsheet source can be a path or an in-memory upload (BytesIO, file).
ExcelSource = Union[str, Path, IO[bytes]]

SHEET_CONTRACTS = "Existing_Provider_Contracts"
SHEET_CHANGES = "Requested_Contract_Changes"
SHEET_RULES = "Validation_Rules"


def _read_sheet(source: ExcelSource, sheet: str) -> pd.DataFrame:
    """Read a sheet without coercing literal ``N/A`` strings into NaN.

    ``keep_default_na=False`` keeps controlled-vocabulary values like ``N/A``
    intact; genuinely empty cells arrive as ``""`` and are normalized by ``_clean``.

    ``source`` may be a path or a file-like object (e.g. an uploaded workbook).
    """
    if hasattr(source, "seek"):
        source.seek(0)  # rewind uploaded buffers so re-reads succeed
    return pd.read_excel(
        source, sheet_name=sheet, dtype=object, keep_default_na=False, na_values=[]
    )


class IntegrityError(AssertionError):
    """Raised when the workbook violates a required data invariant."""


def _clean(value: Any) -> Any:
    """Normalize a raw cell value: NaN/empty-string -> None, else pass through."""
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    try:
        if pd.isna(value):  # pandas NaT / NaN
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return value


def _records(df: pd.DataFrame, pk: str) -> list[dict[str, Any]]:
    """Turn a sheet DataFrame into cleaned dict rows, dropping blank-PK rows."""
    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        record = {col: _clean(row[col]) for col in df.columns}
        if record.get(pk) in (None, ""):
            continue  # trailing/blank spreadsheet rows
        rows.append(record)
    return rows


def load_contracts(
    source: ExcelSource = DEFAULT_REFERENCE,
) -> dict[str, ProviderContract]:
    """Load ``Existing_Provider_Contracts`` keyed by ``provider_contract_id``."""
    df = _read_sheet(source, SHEET_CONTRACTS)
    contracts: dict[str, ProviderContract] = {}
    for rec in _records(df, "provider_contract_id"):
        contract = ProviderContract(**rec)
        contracts[contract.provider_contract_id] = contract
    return contracts


def load_changes(source: ExcelSource = DEFAULT_CHANGES) -> list[ChangeRequest]:
    """Load ``Requested_Contract_Changes`` as an ordered list of change requests.

    ``source`` may be a path or a file-like object (an uploaded input file).
    """
    df = _read_sheet(source, SHEET_CHANGES)
    return [ChangeRequest(**rec) for rec in _records(df, "change_request_id")]


def load_rules(source: ExcelSource = DEFAULT_REFERENCE) -> list[RuleSpec]:
    """Load the human-readable rulebook, enriched with failure outcomes from config."""
    df = _read_sheet(source, SHEET_RULES)
    cfg = load_rules_config().get("rules", {})
    specs: list[RuleSpec] = []
    for rec in _records(df, "rule_id"):
        rid = rec["rule_id"]
        meta = cfg.get(rid, {})
        failure = meta.get("failure_outcome")
        specs.append(
            RuleSpec(
                rule_id=rid,
                validation_rule=rec.get("validation_rule", ""),
                manual_or_application_basis=rec.get("manual_or_application_basis"),
                applies_to_change_category=rec.get("applies_to_change_category") or "All",
                expected_action_when_failed=rec.get("expected_action_when_failed"),
                failure_outcome=Outcome(failure) if failure else None,
            )
        )
    return specs


def _assert_integrity(
    contracts: dict[str, ProviderContract], changes: list[ChangeRequest]
) -> None:
    """Enforce zero-orphan links and in-vocabulary labels; raise with offenders."""
    orphans = [
        c.change_request_id
        for c in changes
        if c.linked_provider_contract_id not in contracts
    ]
    if orphans:
        raise IntegrityError(
            f"{len(orphans)} change request(s) link to a missing contract: {orphans}"
        )

    valid = set(Outcome)
    bad = [
        (c.change_request_id, c.expected_validation_outcome)
        for c in changes
        if c.expected_validation_outcome is not None
        and c.expected_validation_outcome not in valid
    ]
    if bad:
        raise IntegrityError(f"Outcome(s) outside controlled vocabulary: {bad}")


def load_all(
    reference_source: ExcelSource = DEFAULT_REFERENCE,
    changes_source: ExcelSource = DEFAULT_CHANGES,
) -> dict[str, Any]:
    """Load reference + input data into typed models and assert data invariants.

    Contracts and the rulebook come from ``reference_source``; change requests come
    from ``changes_source`` (a path or an uploaded file-like object). Returns
    ``{"contracts": {id: ProviderContract}, "changes": [ChangeRequest],
    "rules": [RuleSpec]}``.
    """
    contracts = load_contracts(reference_source)
    rules = load_rules(reference_source)
    changes = load_changes(changes_source)
    _assert_integrity(contracts, changes)
    return {"contracts": contracts, "changes": changes, "rules": rules}
