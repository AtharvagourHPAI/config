"""Streamlit entrypoint for the Provider Contract Change Validation Engine.

Reviewer UI with two tabs: a single-decision trace viewer and a batch report.
This layer imports only from ``engine`` — no business logic lives here.

Run with:  streamlit run app/main.py
"""

from __future__ import annotations

import pathlib
import sys

# Make the project root importable so `import engine` works, and the app
# directory importable so `import components` works under both `streamlit run`
# and the AppTest harness.
ROOT = pathlib.Path(__file__).resolve().parent.parent
APP_DIR = pathlib.Path(__file__).resolve().parent
for _p in (str(ROOT), str(APP_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import streamlit as st  # noqa: E402

from engine.decision_engine import decide  # noqa: E402
from engine.loaders import DEFAULT_REFERENCE, load_contracts, load_rules  # noqa: E402

from components.batch_report import render_batch  # noqa: E402
from components.input_page import render_input  # noqa: E402
from components.outcome_explorer import render_outcomes  # noqa: E402
from components.reference_viewer import (  # noqa: E402
    load_reference_sheets,
    render_reference,
    render_reference_sidebar,
)
from components.selector import render_selector  # noqa: E402
from components.theme import CSS  # noqa: E402
from components.trace_viewer import render_trace  # noqa: E402

ASSETS = pathlib.Path(__file__).resolve().parent / "assets"

st.set_page_config(
    page_title="healthplans.ai · Provider Contract Change Validation Engine",
    page_icon=str(ASSETS / "dash.png"),
    layout="wide",
)
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_resource(show_spinner="Loading reference data…")
def _reference():
    """Load the fixed reference (existing contracts + rulebook) once."""
    return {"contracts": load_contracts(), "rules": load_rules()}


@st.cache_data(show_spinner=False)
def _reference_sheets():
    """Load the reference workbook sheets as DataFrames for the viewer."""
    return load_reference_sheets(str(DEFAULT_REFERENCE))


reference = _reference()
contracts = reference["contracts"]
reference_sheets = _reference_sheets()

# --- Sidebar / brand ---
with st.sidebar:
    dash = ASSETS / "dash.png"
    logo = ASSETS / "logo.png"
    if dash.exists():
        st.image(str(dash), width=120)
    if logo.exists():
        st.image(str(logo), width=210)
    else:
        st.markdown("### healthplans.ai")
    st.caption("Provider Contract Change Validation Engine · CMS-855I")
    st.divider()
    render_reference_sidebar(reference_sheets)
    st.divider()
    processed = st.session_state.get("processed", False)
    scored = (
        st.session_state["report"]["total"] if processed else "—"
    )
    st.markdown(
        f"**{len(contracts)}** reference contracts  \n"
        f"**{len(reference['rules'])}** validation rules  \n"
        f"**{scored}** change requests scored"
    )
    if processed:
        st.caption(f"Input: {st.session_state.get('source_label', '—')}")
    st.caption(
        "Deterministic, rule-driven decisions. Every outcome cites the rules and "
        "tags that produced it."
    )

st.title("Provider Contract Change Validation Engine")
st.caption("Rule-driven · deterministic · fully explainable")

# A selected reference sheet opens as a focused view above everything else.
if st.session_state.get("ref_sheet"):
    render_reference(reference_sheets, st.session_state["ref_sheet"])
    st.stop()

tab_input, tab_outcomes, tab_single, tab_batch = st.tabs(
    ["Input", "Outcomes", "Single decision", "Batch report"]
)

with tab_input:
    render_input(reference)

_NOT_READY = (
    "No input processed yet. Go to the **Input** tab, upload a contract-change "
    "file (or use the sample), and click **Process**."
)

with tab_outcomes:
    if not st.session_state.get("processed"):
        st.info(_NOT_READY)
    else:
        report = st.session_state["report"]
        changes_by_id = {
            c.change_request_id: c for c in st.session_state["bundle"]["changes"]
        }
        render_outcomes(report, contracts, changes_by_id)

with tab_single:
    if not st.session_state.get("processed"):
        st.info(_NOT_READY)
    else:
        changes = st.session_state["bundle"]["changes"]
        change = render_selector(changes)
        contract = contracts[change.linked_provider_contract_id]
        decision = decide(change, contract)
        render_trace(change, contract, decision)

        # Ground-truth label for reviewer reference (never read by decide()).
        if change.expected_validation_outcome:
            match = change.expected_validation_outcome == decision.outcome
            st.caption(
                f"Labeled (ground-truth) outcome: "
                f"{change.expected_validation_outcome.value} "
                f"{'✓ matches' if match else '✗ differs from'} engine."
            )

with tab_batch:
    if not st.session_state.get("processed"):
        st.info(_NOT_READY)
    else:
        report = st.session_state["report"]
        changes_by_id = {
            c.change_request_id: c for c in st.session_state["bundle"]["changes"]
        }
        render_batch(report, contracts, changes_by_id)
