# healthplans.ai — Contract Validation Engine (Enhanced, Light Theme)

Reviewer dashboard for the Provider Contract Change Validation Engine (CMS-855I),
on a **light, atmospheric background**. Two builds:

```
html/                    Standalone web version — open and go
  index.html
  assets/  dash.png · logo.png · logo-ink.png

react/                   React component
  ValidationEngine.jsx
  assets/  dash.png · logo.png · logo-ink.png
```

> You said you only need the **web version** — that's the `html/` folder. Just open
> `html/index.html` in a browser (keep `assets/` beside it). The `react/` folder is
> optional and only for a React app.

## What's new vs. the first version

**Single decision**
- **Sticky verdict header** — outcome, contract action, winning rule, and "match ✓" stay pinned while you scroll the evidence.
- **Decision path ladder** — shows the precedence tiers (adverse → procedural → cross-state → develop → approve); the tier that fired is highlighted, later tiers are visibly skipped. This explains *why this outcome won over another*.
- **Before → after diffs** — Change actions render the old value struck-through and the new value highlighted, not just two table rows.
- **Failing-path treatment** — defaults to a DENY case so red FAIL, the "verdict on fail" chip, and the ★ deciding rule are all visible.
- **Reviewer actions** — context-aware buttons (Refer for review / Issue development request / Route to enrollment / Confirm & apply) plus **Export** (downloads the decision trace as JSON for the audit file).
- **Timestamp + rulebook version** on the ground-truth match line.

**Batch report (new tab, fully built)**
- Four KPIs (scored, accuracy, straight-through, routed).
- **Confusion matrix** (predicted vs. labeled, diagonal highlighted).
- **Outcome distribution** donut with REJECT flagged "rule-only".
- **Per-category accuracy** bars.
- **Data & model notes** calling out the 82% APPROVE imbalance, REJECT = 0 (rule-only + synthetic fixtures), and the R-005 / R-003 signals.
- **Filterable results table** with match indicators and a "No mismatches" empty state; click any in-dataset row to jump to its full trace.

## Design
- Light theme with a layered radial-gradient + subtle dot-grid background.
- Fonts: Fraunces (display) · Manrope (body) · JetBrains Mono (IDs/data).
- Accent keyed to the mascot's cyan; per-outcome color system (approve/develop/deny/reject/initial).
- No UI libraries — pure CSS + inline SVG.

## Notes
- `logo-ink.png` is a transparent dark-ink version of the wordmark (the original `logo.png` is black-on-black and only shows on dark surfaces).
- All data is mock fixtures inside the file — wire to your engine API by replacing the `REQUESTS`, `RESULTS`, `DIST`, and `CATS` constants.
- React asset imports assume a bundler (Vite/CRA/Next); swap for hosted URLs otherwise.

### Tip: hide Streamlit's "Deploy" chrome
If you port this look back into Streamlit, hide the default menu/Deploy button via
`Settings → hide` or `.streamlit/config.toml` so it reads as a product, not a notebook.
