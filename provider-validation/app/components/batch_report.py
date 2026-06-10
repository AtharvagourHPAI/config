"""Batch report component: accuracy, distribution, confusion matrix, mismatches."""

from __future__ import annotations

from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from engine.enums import Outcome

from .theme import kpi, outcome_label
from .trace_viewer import render_trace


def _distribution_frame(report: dict[str, Any]) -> pd.DataFrame:
    expected = report["distribution"]["expected"]
    actual = report["distribution"]["actual"]
    order = [o.value for o in Outcome]
    return pd.DataFrame(
        {
            "Expected": [expected.get(o, 0) for o in order],
            "Actual": [actual.get(o, 0) for o in order],
        },
        index=[outcome_label(o) for o in order],
    )


def _clustered_column_chart(dist: pd.DataFrame) -> alt.Chart:
    """Clustered (grouped) column chart: Expected vs. Actual per outcome."""
    long = (
        dist.rename_axis("Outcome")
        .reset_index()
        .melt(id_vars="Outcome", var_name="Series", value_name="Count")
    )
    order = list(dist.index)
    return (
        alt.Chart(long)
        .mark_bar()
        .encode(
            x=alt.X("Outcome:N", sort=order, title=None, axis=alt.Axis(labelAngle=-20)),
            xOffset=alt.XOffset("Series:N"),
            y=alt.Y("Count:Q", title="Requests"),
            color=alt.Color(
                "Series:N",
                title=None,
                scale=alt.Scale(
                    domain=["Expected", "Actual"], range=["#9bb4cf", "#2f7dc6"]
                ),
                legend=alt.Legend(orient="top"),
            ),
            tooltip=["Outcome", "Series", "Count"],
        )
        .properties(height=300)
    )


def _confusion_frame(report: dict[str, Any]) -> pd.DataFrame:
    order = [o.value for o in Outcome]
    matrix = pd.DataFrame(0, index=order, columns=order)
    for (expected, predicted), count in report["confusion"].items():
        matrix.loc[expected, predicted] = count
    labels = [outcome_label(o) for o in order]
    matrix.index = labels
    matrix.columns = labels
    return matrix


def render_batch(report: dict[str, Any], contracts: dict, changes_by_id: dict) -> None:
    """Render the full batch scoring report."""
    correct, total = report["correct"], report["total"]
    accuracy = report["accuracy"]

    cols = st.columns(4)
    cols[0].markdown(kpi(str(total), "Requests scored"), unsafe_allow_html=True)
    cols[1].markdown(kpi(f"{correct}/{total}", "Outcome matches"), unsafe_allow_html=True)
    cols[2].markdown(kpi(f"{accuracy:.0%}", "Engine accuracy"), unsafe_allow_html=True)
    cols[3].markdown(
        kpi(str(len(report["mismatches"])), "Mismatches"), unsafe_allow_html=True
    )

    st.divider()
    left, right = st.columns([3, 2])
    with left:
        st.markdown("##### Expected vs. actual distribution")
        dist = _distribution_frame(report)
        st.altair_chart(_clustered_column_chart(dist), use_container_width=True)
        st.dataframe(dist, use_container_width=True)
    with right:
        st.markdown("##### Per-category accuracy")
        per_cat = pd.DataFrame(
            {"Accuracy": {k: f"{v:.0%}" for k, v in report["per_category"].items()}}
        )
        st.dataframe(per_cat, use_container_width=True)

    st.markdown("##### Confusion matrix (rows = expected, cols = predicted)")
    st.dataframe(_confusion_frame(report), use_container_width=True)

    st.divider()
    st.markdown("##### Mismatches")
    mismatches = report["mismatches"]
    if not mismatches:
        st.success(
            f"No mismatches — all labeled outcomes reproduced ({correct}/{total})."
        )
    else:
        for m in mismatches:
            with st.expander(
                f"{m['change_request_id']} — expected {outcome_label(m['expected'])}, "
                f"got {outcome_label(m['predicted'])}"
            ):
                change = changes_by_id[m["change_request_id"]]
                contract = contracts[change.linked_provider_contract_id]
                render_trace(change, contract, m["decision"])
