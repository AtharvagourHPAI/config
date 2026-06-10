"""Outcome explorer: clickable result cards -> contract list -> plain-language detail.

After an input file is processed, this view shows one card per outcome
(APPROVE / DEVELOP / DENY / REJECT / INITIAL_ENROLLMENT_REQUIRED) with a count.
Clicking a card lists the change requests that landed on that outcome; clicking a
specific request explains, in everyday language, *what* the engine decided and
*why*. The full technical trace stays available in an expander.

This is a presentation layer only — it reads the already-computed ``report`` and
never re-runs decision logic.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from engine.enums import Outcome
from engine.models import ChangeRequest, Decision, ProviderContract

from .theme import OUTCOME_COLORS, badge, outcome_label
from .trace_viewer import render_trace

# Session keys for the drill-down state.
_SEL_OUTCOME = "oe_outcome"
_SEL_REQUEST = "oe_request"

# One-line, friendly headline per outcome.
_OUTCOME_HEADLINE = {
    "APPROVE": "Approved — the change will be applied",
    "DEVELOP": "Needs more information before we can decide",
    "DENY": "Denied — the change cannot be made",
    "REJECT": "Returned to the provider — submission can't be processed as-is",
    "INITIAL_ENROLLMENT_REQUIRED": "Needs a separate initial enrollment",
}

# Plain-language reason keyed by the winning rule.
_REASON_BY_RULE = {
    "R-001": "the request came in on the wrong CMS form (it must be filed on CMS-855I)",
    "R-002": "the provider identifiers on the request did not match the contract on file",
    "R-003": "it adds a practice location in a different state, which can't be handled as a simple change",
    "R-004": "the special payment address is not one of the allowed destination types",
    "R-005": "a final adverse legal action (such as an exclusion or debarment) is on record",
    "R-006": "the reassignment target could not be confirmed as an enrolled Medicare group",
    "R-007": "required EFT bank documentation (CMS-588 / voided check or bank letter) is missing",
    "R-008": "the certification statement was not signed",
    "R-009": "the requested specialty is not compatible with the provider's type or licensure",
    "R-010": "additional supporting documentation is still needed",
}


def _change_phrase(change: ChangeRequest) -> str:
    action = change.change_action.value.lower()
    category = change.change_category.value
    old = change.existing_value or "not set"
    new = change.requested_new_value or "not set"
    return (
        f"a request to **{action}** the provider's **{category}** "
        f'(from "{old}" to "{new}")'
    )


def layman_summary(
    change: ChangeRequest, contract: ProviderContract, decision: Decision
) -> str:
    """Return a short, plain-English explanation of the decision and the reasoning."""
    provider = contract.individual_name or contract.legal_business_name or "the provider"
    outcome = decision.outcome.value
    headline = _OUTCOME_HEADLINE.get(outcome, outcome)
    phrase = _change_phrase(change)
    reason = _REASON_BY_RULE.get(decision.winning_rule or "")

    if outcome == "APPROVE":
        body = (
            f"This was {phrase} for **{provider}**. "
            "Every applicable check passed, so the engine **approved** it and the "
            "update will be applied to the provider's contract."
        )
    elif outcome == "REJECT":
        body = (
            f"This was {phrase} for **{provider}**. "
            f"The engine **returned the submission to the provider** because {reason}. "
            "Nothing is changed on the contract — the provider needs to fix the "
            "paperwork and resubmit."
        )
    elif outcome == "DENY":
        body = (
            f"This was {phrase} for **{provider}**. "
            f"The engine **denied** it because {reason}. This is a decision on the "
            "merits, so the change is not applied and the case is referred for review."
        )
    elif outcome == "DEVELOP":
        body = (
            f"This was {phrase} for **{provider}**. "
            f"The engine could **not decide yet** because {reason}. A development "
            "request is issued asking the provider for the missing information; the "
            "case is re-evaluated once that comes back."
        )
    elif outcome == "INITIAL_ENROLLMENT_REQUIRED":
        body = (
            f"This was {phrase} for **{provider}**. "
            "It can't be processed as a change to the existing contract because it "
            "adds an out-of-state practice location, which requires a brand-new "
            "**initial enrollment** application instead."
        )
    else:  # pragma: no cover - defensive
        body = f"This was {phrase} for **{provider}**. Outcome: {outcome}."

    rule_note = (
        f" The deciding rule was `{decision.winning_rule}`."
        if decision.winning_rule
        else " No rule needed to fire — all checks passed."
    )
    next_step = f" **Next step:** {decision.contract_action}."
    return f"**{headline}.** " + body + rule_note + next_step


def _group_by_outcome(report: dict[str, Any]) -> dict[str, list[str]]:
    """Map each outcome value to the list of change_request_ids that produced it."""
    groups: dict[str, list[str]] = {o.value: [] for o in Outcome}
    for cid, decision in report["decisions"].items():
        groups[decision.outcome.value].append(cid)
    for cid_list in groups.values():
        cid_list.sort()
    return groups


def _render_cards(groups: dict[str, list[str]]) -> None:
    st.markdown("##### Decision outcomes")
    st.caption("Click an outcome to see the contracts that landed on it.")
    order = [o.value for o in Outcome]
    cols = st.columns(len(order))
    for col, outcome in zip(cols, order):
        count = len(groups[outcome])
        color = OUTCOME_COLORS.get(outcome, "#647389")
        with col:
            st.markdown(
                f"""
                <div class="ocard" style="border-top:4px solid {color}">
                  <div class="ocard-n" style="color:{color}">{count}</div>
                  <div class="ocard-l">{outcome_label(outcome)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(
                f"View {count}",
                key=f"oe_card_{outcome}",
                use_container_width=True,
                disabled=count == 0,
            ):
                st.session_state[_SEL_OUTCOME] = outcome
                st.session_state.pop(_SEL_REQUEST, None)
                st.rerun()


def _render_list(
    outcome: str, groups: dict[str, list[str]], changes_by_id: dict, contracts: dict
) -> None:
    top = st.columns([1, 5])
    with top[0]:
        if st.button("← All outcomes", key="oe_back_to_cards", use_container_width=True):
            st.session_state.pop(_SEL_OUTCOME, None)
            st.session_state.pop(_SEL_REQUEST, None)
            st.rerun()
    with top[1]:
        st.markdown(badge(outcome, outcome_label(outcome)), unsafe_allow_html=True)

    cids = groups.get(outcome, [])
    st.markdown(
        f"##### {len(cids)} contract change request(s) · {outcome_label(outcome)}"
    )
    if not cids:
        st.info("No change requests produced this outcome for the current input.")
        return

    st.caption("Click a request to see a plain-language explanation of the decision.")
    for cid in cids:
        change = changes_by_id[cid]
        contract = contracts[change.linked_provider_contract_id]
        provider = contract.individual_name or contract.legal_business_name or "—"
        label = (
            f"{cid}  ·  {provider}  ·  "
            f"{change.change_category.value} ({change.change_action.value})  ·  "
            f"contract {change.linked_provider_contract_id}"
        )
        if st.button(label, key=f"oe_req_{cid}", use_container_width=True):
            st.session_state[_SEL_REQUEST] = cid
            st.rerun()


def _render_detail(
    cid: str, outcome: str, report: dict[str, Any], changes_by_id: dict, contracts: dict
) -> None:
    change = changes_by_id[cid]
    contract = contracts[change.linked_provider_contract_id]
    decision = report["decisions"][cid]

    top = st.columns([1, 1, 4])
    with top[0]:
        if st.button("← All outcomes", key="oe_detail_to_cards", use_container_width=True):
            st.session_state.pop(_SEL_OUTCOME, None)
            st.session_state.pop(_SEL_REQUEST, None)
            st.rerun()
    with top[1]:
        if st.button(
            f"← {outcome_label(outcome)} list",
            key="oe_detail_to_list",
            use_container_width=True,
        ):
            st.session_state.pop(_SEL_REQUEST, None)
            st.rerun()

    st.markdown(f"##### {cid}")
    st.markdown(
        badge(decision.outcome.value, outcome_label(decision.outcome.value)),
        unsafe_allow_html=True,
    )

    color = OUTCOME_COLORS.get(decision.outcome.value, "#647389")
    summary = layman_summary(change, contract, decision)
    st.markdown(
        f"<div class='summary-card' style='border-left:5px solid {color}'>{summary}</div>",
        unsafe_allow_html=True,
    )

    # Ground-truth label (reviewer reference only; never read by decide()).
    if change.expected_validation_outcome:
        match = change.expected_validation_outcome == decision.outcome
        st.caption(
            f"Labeled (ground-truth) outcome: "
            f"{change.expected_validation_outcome.value} "
            f"{'✓ matches' if match else '✗ differs from'} engine."
        )

    with st.expander("Show the full technical trace (rules, tags, verdicts)"):
        render_trace(change, contract, decision)


def render_outcomes(report: dict[str, Any], contracts: dict, changes_by_id: dict) -> None:
    """Render the cards -> list -> detail drill-down for the processed input."""
    groups = _group_by_outcome(report)

    selected_outcome = st.session_state.get(_SEL_OUTCOME)
    selected_request = st.session_state.get(_SEL_REQUEST)

    # Guard against stale selections (e.g. after re-processing a new input).
    if selected_request and selected_request not in report["decisions"]:
        st.session_state.pop(_SEL_REQUEST, None)
        selected_request = None
    if selected_outcome and selected_outcome not in groups:
        st.session_state.pop(_SEL_OUTCOME, None)
        selected_outcome = None

    if selected_outcome and selected_request:
        _render_detail(selected_request, selected_outcome, report, changes_by_id, contracts)
    elif selected_outcome:
        _render_list(selected_outcome, groups, changes_by_id, contracts)
    else:
        _render_cards(groups)
