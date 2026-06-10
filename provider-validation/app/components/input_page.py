"""Input page: upload a contract-change input file, validate it, and process it.

The reference data (existing contracts + rulebook) is fixed and ships with the
app. The reviewer supplies the *input* — a ``Requested_Contract_Changes`` workbook
— here. On process, the engine scores every row and the dashboard tabs unlock.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from engine.enums import Outcome
from engine.loaders import (
    DEFAULT_CHANGES,
    IntegrityError,
    _assert_integrity,
    load_changes,
)
from engine.scoring import score_all

from .theme import outcome_label


def _process(reference: dict[str, Any], changes_source: Any, label: str) -> None:
    """Load + integrity-check + score one input source; stash results in session.

    The reference (contracts + rules) is already in memory, so only the change
    requests are parsed from the uploaded/selected source.
    """
    try:
        changes = load_changes(changes_source)
        _assert_integrity(reference["contracts"], changes)
    except IntegrityError as exc:
        st.error(f"Input rejected — referential integrity failed: {exc}")
        return
    except Exception as exc:  # malformed workbook, wrong sheet, etc.
        st.error(
            "Could not read the input file. Make sure it is an .xlsx with a "
            f"'Requested_Contract_Changes' sheet. Details: {exc}"
        )
        return

    bundle = {
        "contracts": reference["contracts"],
        "rules": reference["rules"],
        "changes": changes,
    }
    report = score_all(data=bundle)

    st.session_state["bundle"] = bundle
    st.session_state["report"] = report
    st.session_state["source_label"] = label
    st.session_state["processed"] = True


def _distribution_preview(changes: list) -> pd.DataFrame:
    counts = {o.value: 0 for o in Outcome}
    for c in changes:
        if c.expected_validation_outcome:
            counts[c.expected_validation_outcome.value] += 1
    labeled = {outcome_label(o): n for o, n in counts.items()}
    return pd.DataFrame({"Labeled rows": labeled})


def render_input(reference: dict[str, Any]) -> None:
    """Render the upload + process page."""
    st.markdown("##### 1 · Contract change input file")
    st.caption(
        "The reference data (existing contracts and the rulebook) is fixed and "
        "loaded automatically — browse it from the **Reference data** buttons in the "
        "sidebar. Here you only supply the change-request input to score."
    )
    upload = st.file_uploader(
        "Upload a contract-change input workbook (.xlsx with a "
        "'Requested_Contract_Changes' sheet)",
        type=["xlsx"],
    )

    cols = st.columns([1, 1, 2])
    with cols[0]:
        process_clicked = st.button(
            "Process uploaded file",
            type="primary",
            disabled=upload is None,
            use_container_width=True,
        )
    with cols[1]:
        sample_clicked = st.button(
            "Use sample input",
            use_container_width=True,
        )

    if process_clicked and upload is not None:
        _process(reference, upload, f"Uploaded · {upload.name}")
    elif sample_clicked:
        _process(reference, DEFAULT_CHANGES, "Bundled sample input")

    if st.session_state.get("processed"):
        report = st.session_state["report"]
        changes = st.session_state["bundle"]["changes"]
        st.divider()
        st.markdown("##### 2 · Processed")
        st.success(
            f"Processed **{st.session_state.get('source_label', 'input')}** — "
            f"{report['total']} change requests scored. "
            "Open the **Outcomes** tab to explore the decisions."
        )
        st.dataframe(
            _distribution_preview(changes).T, use_container_width=True
        )
    else:
        st.info(
            "Upload an input file and click **Process**, or click **Use sample "
            "input** to explore the bundled data."
        )
