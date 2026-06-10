"""Decision-trace component: outcome, action, tags, and per-rule verdicts."""

from __future__ import annotations

import html

import streamlit as st

from engine.models import ChangeRequest, Decision, ProviderContract

from .theme import badge, chip, outcome_label


def _fmt(value) -> str:
    if value is None:
        return "—"
    return html.escape(str(value))


def _kv_table(rows: list[tuple[str, object]]) -> str:
    body = "".join(
        f"<tr><td style='color:#647389;padding:3px 14px 3px 0;white-space:nowrap'>{k}</td>"
        f"<td class='mono'>{_fmt(v)}</td></tr>"
        for k, v in rows
    )
    return f"<table style='border-collapse:collapse'>{body}</table>"


def render_trace(
    change: ChangeRequest, contract: ProviderContract, decision: Decision
) -> None:
    """Render the full decision trace for one change request."""
    # --- Outcome banner ---
    top = st.columns([2, 3])
    with top[0]:
        st.markdown(
            badge(decision.outcome.value, outcome_label(decision.outcome.value)),
            unsafe_allow_html=True,
        )
        st.markdown(
            f"**Contract action:** {decision.contract_action}", unsafe_allow_html=True
        )
        if decision.winning_rule:
            st.markdown(
                f"**Winning rule:** `{decision.winning_rule}`", unsafe_allow_html=True
            )
    with top[1]:
        st.caption("Explanation")
        st.write(decision.explanation)

    # --- Change vs. contract, side by side ---
    st.divider()
    cols = st.columns(2)
    with cols[0]:
        st.markdown("##### Requested change")
        st.markdown(
            _kv_table(
                [
                    ("Request ID", change.change_request_id),
                    ("Category", change.change_category.value),
                    ("Action", change.change_action.value),
                    ("CMS form", change.cms_form),
                    ("Existing value", change.existing_value),
                    ("Requested value", change.requested_new_value),
                    ("New location state", change.new_location_state),
                    ("Same state?", change.new_location_same_state.value),
                    ("Signature present", change.provider_signature_present.value),
                    ("Development requested", change.development_requested.value),
                    (
                        "Development due",
                        change.development_response_due_date,
                    ),
                    (
                        "Screening",
                        change.screening_required.value
                        if change.screening_required
                        else None,
                    ),
                ]
            ),
            unsafe_allow_html=True,
        )
    with cols[1]:
        st.markdown("##### Current contract (source of truth)")
        st.markdown(
            _kv_table(
                [
                    ("Contract ID", contract.provider_contract_id),
                    ("Provider", contract.individual_name),
                    ("NPI", contract.npi),
                    ("PTAN", contract.ptan),
                    ("TIN/SSN key", contract.tax_id_or_ssn_key),
                    ("Legal business name", contract.legal_business_name),
                    ("Provider type", contract.provider_type),
                    ("Primary specialty", contract.primary_specialty),
                    ("Contract status", contract.contract_status.value if contract.contract_status else None),
                    ("PECOS status", contract.pecos_enrollment_status),
                    ("Practice state", contract.practice_state),
                    ("Sanction screening", contract.sanction_screening_status),
                ]
            ),
            unsafe_allow_html=True,
        )

    # --- Fired tags ---
    st.divider()
    st.markdown("##### Derived tags")
    fired = decision.tags.fired()
    if fired:
        st.markdown("".join(chip(t) for t in fired), unsafe_allow_html=True)
    else:
        st.caption("No notable tags fired.")
    if decision.tags.screening_tier:
        st.caption(f"Screening tier: {decision.tags.screening_tier.value}")

    # --- Evaluated rules ---
    st.markdown("##### Evaluated rules")
    header = (
        "<tr style='text-align:left;border-bottom:2px solid #e6ebf1'>"
        "<th style='padding:6px 12px'>Rule</th><th style='padding:6px 12px'>Result</th>"
        "<th style='padding:6px 12px'>Verdict on fail</th><th style='padding:6px 12px'>Message</th></tr>"
    )
    body = ""
    for r in decision.evaluated_rules:
        win = r.rule_id == decision.winning_rule
        row_cls = "winrow" if win else ""
        result = (
            "<span class='rulepass'>PASS</span>"
            if r.passed
            else "<span class='rulefail'>FAIL</span>"
        )
        star = " ★" if win else ""
        verdict = outcome_label(r.verdict.value) if r.verdict else "—"
        body += (
            f"<tr class='{row_cls}' style='border-bottom:1px solid #eef2f7'>"
            f"<td class='mono' style='padding:6px 12px'>{r.rule_id}{star}</td>"
            f"<td style='padding:6px 12px'>{result}</td>"
            f"<td class='mono' style='padding:6px 12px'>{verdict}</td>"
            f"<td style='padding:6px 12px'>{html.escape(r.message)}</td></tr>"
        )
    st.markdown(
        f"<table style='border-collapse:collapse;width:100%'>{header}{body}</table>",
        unsafe_allow_html=True,
    )
    st.caption("★ winning rule")
