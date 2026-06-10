"""Shared visual helpers for the Streamlit UI (healthplans.ai / Dash branding).

Pure presentation only — no business logic. Colors use the healthplans.ai accent
palette (cyan/blue) on a soft, light background.
"""

from __future__ import annotations

OUTCOME_COLORS = {
    "APPROVE": "#1f9d6b",
    "DEVELOP": "#2f7dc6",
    "DENY": "#d3493f",
    "REJECT": "#c77d1a",
    "INITIAL_ENROLLMENT_REQUIRED": "#7a4fb0",
}

# Friendly display labels for outcomes (engine values stay unchanged).
OUTCOME_LABELS = {
    "DEVELOP": "Missing information",
}


def outcome_label(outcome: str) -> str:
    """Return the user-facing label for an outcome value."""
    return OUTCOME_LABELS.get(outcome, outcome.replace("_", " "))

CYAN = "#5cc6e8"
NAVY = "#0b1320"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Manrope:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"] { font-family: "Manrope", system-ui, sans-serif; }
h1, h2, h3 { font-family: "Fraunces", serif !important; letter-spacing: -0.01em; color:#16202f; }

/* App canvas -> soft light wash */
[data-testid="stAppViewContainer"] {
  background: radial-gradient(620px 320px at 88% -8%, rgba(92,198,232,.16), transparent 70%),
              linear-gradient(180deg,#f6f9fc,#eef3f9 60%);
}
[data-testid="stHeader"] { background: transparent; }

/* Sidebar -> light, with a faint cyan glow */
section[data-testid="stSidebar"] {
  background: radial-gradient(360px 200px at 30% -10%, rgba(92,198,232,.20), transparent 70%),
              linear-gradient(180deg,#ffffff,#eef4fa 70%);
  border-right: 1px solid #e3eaf2;
}
section[data-testid="stSidebar"] * { color: #243349; }
section[data-testid="stSidebar"] h3 { color:#16202f; }

/* Center + align the brand images (dash + healthplans.ai logo) in the sidebar */
section[data-testid="stSidebar"] [data-testid="stImage"] { text-align:center; margin:0 auto; }
section[data-testid="stSidebar"] [data-testid="stImage"] img { margin:0 auto; display:block; }

.badge {
  display:inline-block; padding:6px 14px; border-radius:999px;
  font-weight:800; font-size:13px; letter-spacing:.02em; color:#fff;
  font-family:"JetBrains Mono", monospace;
}
.chip {
  display:inline-block; margin:3px 5px 3px 0; padding:4px 11px; border-radius:999px;
  background:#eaf6fb; border:1px solid #cdeaf5; color:#1d5a72;
  font-size:12px; font-weight:600; font-family:"JetBrains Mono", monospace;
}
.kpi {
  background:#fff; border:1px solid #e6ebf1; border-radius:16px; padding:18px 20px;
  box-shadow:0 1px 2px rgba(16,32,56,.04),0 8px 24px rgba(16,32,56,.06);
}
.kpi .v { font-family:"Fraunces", serif; font-size:30px; font-weight:700; color:#16202f; }
.kpi .l { color:#647389; font-size:12.5px; font-weight:700; text-transform:uppercase; letter-spacing:.08em; }
.rulepass { color:#1f9d6b; font-weight:800; }
.rulefail { color:#d3493f; font-weight:800; }
.winrow { background:#fff8ec; }
.mono { font-family:"JetBrains Mono", monospace; font-size:12.5px; }

/* Outcome drill-down cards */
.ocard {
  background:#fff; border:1px solid #e6ebf1; border-radius:16px;
  padding:16px 14px 14px; text-align:center;
  box-shadow:0 1px 2px rgba(16,32,56,.04),0 8px 24px rgba(16,32,56,.06);
  margin-bottom:8px;
}
.ocard-n { font-family:"Fraunces", serif; font-size:34px; font-weight:700; line-height:1.1; }
.ocard-l {
  color:#647389; font-size:11px; font-weight:700; text-transform:uppercase;
  letter-spacing:.06em; margin-top:4px; min-height:28px;
}
.summary-card {
  background:#fff; border:1px solid #e6ebf1; border-radius:14px;
  padding:16px 18px; margin:10px 0 6px; line-height:1.55; font-size:15px;
  box-shadow:0 1px 2px rgba(16,32,56,.04),0 8px 24px rgba(16,32,56,.06);
}
</style>
"""


def badge(outcome: str, label: str | None = None) -> str:
    """Return HTML for a colored outcome badge (color by value, text by label)."""
    color = OUTCOME_COLORS.get(outcome, "#647389")
    text = label if label is not None else outcome
    return f'<span class="badge" style="background:{color}">{text}</span>'


def chip(text: str) -> str:
    """Return HTML for a small tag chip."""
    return f'<span class="chip">{text}</span>'


def kpi(value: str, label: str) -> str:
    """Return HTML for a KPI card."""
    return f'<div class="kpi"><div class="v">{value}</div><div class="l">{label}</div></div>'
