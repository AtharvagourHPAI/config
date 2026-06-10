"""Change-request selector component."""

from __future__ import annotations

import streamlit as st

from engine.models import ChangeRequest


def render_selector(changes: list[ChangeRequest]) -> ChangeRequest:
    """Render a selectbox over change requests and return the selected one."""
    by_id = {c.change_request_id: c for c in changes}

    def _label(cid: str) -> str:
        c = by_id[cid]
        return f"{cid}  ·  {c.change_category.value} ({c.change_action.value})"

    selected_id = st.selectbox(
        "Change request",
        options=list(by_id.keys()),
        format_func=_label,
    )
    return by_id[selected_id]
