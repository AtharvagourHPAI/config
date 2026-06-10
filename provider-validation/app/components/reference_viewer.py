"""Reference-data viewer: open a source-of-truth sheet with a plain-language summary.

The reference workbook (``reference_data.xlsx``) is fixed and ships with the app.
The sidebar exposes one button per sheet; selecting one opens it here as a table
alongside a short description of what the dataset is and how the engine uses it.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

# Display order + friendly titles for the reference sheets.
REFERENCE_SHEETS: list[tuple[str, str]] = [
    ("Existing_Provider_Contracts", "Existing provider contracts"),
    ("Validation_Rules", "Validation rules"),
    ("Lists", "Results"),
    ("Summary", "Summary"),
]

# Plain-language description of each reference dataset.
_SUMMARIES: dict[str, str] = {
    "Existing_Provider_Contracts": (
        "The **source-of-truth** record of providers already enrolled on CMS-855I. "
        "Every incoming change request is validated against the matching row here "
        "(identifiers, status, specialty, sanction screening, and more). The engine "
        "treats these contracts as fixed reference state — it never edits them."
    ),
    "Validation_Rules": (
        "The human-readable rulebook (**R-001 … R-010**). Each row describes one "
        "check, which change categories it applies to, and what should happen when "
        "it fails. The engine implements these as deterministic, pure functions, so "
        "every decision can cite the exact rules it evaluated."
    ),
    "Lists": (
        "The **controlled vocabulary** — the closed set of valid values the engine "
        "recognizes, including the five possible outcomes (APPROVE, DEVELOP, DENY, "
        "REJECT, INITIAL_ENROLLMENT_REQUIRED). Anything outside these lists is "
        "rejected at load time to keep decisions predictable."
    ),
    "Summary": (
        "Reference metadata and expected counts for the dataset — a quick at-a-glance "
        "sheet describing the volumes and the expected outcome distribution."
    ),
}


@st.cache_data(show_spinner=False)
def load_reference_sheets(path_str: str) -> dict[str, pd.DataFrame]:
    """Read every reference sheet into a DataFrame (cached by file path)."""
    book = pd.ExcelFile(path_str)
    out: dict[str, pd.DataFrame] = {}
    for sheet, _title in REFERENCE_SHEETS:
        if sheet in book.sheet_names:
            out[sheet] = pd.read_excel(
                path_str, sheet_name=sheet, dtype=object, keep_default_na=False
            )
    return out


def render_reference(sheets: dict[str, pd.DataFrame], active: str) -> None:
    """Render one reference sheet with its summary and a close control."""
    title = dict(REFERENCE_SHEETS).get(active, active)

    head = st.columns([6, 1])
    with head[0]:
        st.markdown(f"### Reference data · {title}")
    with head[1]:
        if st.button("✕ Close", key="ref_close", use_container_width=True):
            st.session_state.pop("ref_sheet", None)
            st.rerun()

    summary = _SUMMARIES.get(active)
    if summary:
        st.markdown(
            f"<div class='summary-card'>{summary}</div>", unsafe_allow_html=True
        )

    df = sheets.get(active)
    if df is None:
        st.warning(f"Sheet '{active}' is not present in the reference workbook.")
        return

    st.caption(f"{len(df)} row(s) × {len(df.columns)} column(s) · {active}")
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_reference_sidebar(sheets: dict[str, pd.DataFrame]) -> None:
    """Render the sidebar buttons that open each reference sheet."""
    st.markdown("##### Reference data")
    st.caption("Source-of-truth datasets")
    for sheet, title in REFERENCE_SHEETS:
        if sheet not in sheets:
            continue
        active = st.session_state.get("ref_sheet") == sheet
        if st.button(
            ("● " if active else "") + title,
            key=f"ref_btn_{sheet}",
            use_container_width=True,
        ):
            st.session_state["ref_sheet"] = sheet
            st.rerun()
