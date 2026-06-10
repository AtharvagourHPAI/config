# Provider Contract Change Validation Engine (CMS-855I)

A **deterministic, explainable** rule engine that validates requested changes to
already-enrolled Medicare CMS-855I provider contracts. Given a change request and
the provider's current contract, it derives tags, evaluates a rulebook, and returns
exactly one of five outcomes — `APPROVE`, `DEVELOP`, `DENY`, `REJECT`,
`INITIAL_ENROLLMENT_REQUIRED` — plus a downstream contract action and a full decision
trace (every rule evaluated, its verdict, and the tags that fired).

The decision path is **rule-driven, not ML-driven**: identical inputs always produce
identical outputs and the same trace.

## Quick start

```bash
pip install -r requirements.txt
pytest                       # 46 tests incl. 72/72 regression, synthetic REJECT, API parity
streamlit run app/main.py    # reviewer UI
uvicorn api.main:app --reload  # REST API (http://127.0.0.1:8000, docs at /docs)
```

> Requires Python 3.11+ (developed/verified on 3.14).

## Input data organization

The raw workbook is split into two purpose-built files (regenerate with
`python tools/build_input_data.py`):

| File | Role | Sheets |
|---|---|---|
| `data/reference_data.xlsx` | **Reference / source of truth** — ships with the app | `Existing_Provider_Contracts`, `Validation_Rules`, `Lists`, `Summary` |
| `data/contract_change_requests.xlsx` | **Input** — the change-request file a reviewer uploads | `Requested_Contract_Changes` |

The original combined workbook (`data/provider_contract_change_request_datasets.xlsx`)
is kept as the master source the split is generated from. The input file includes 12
appended dummy rows so there is a fuller spread of `DENY` and `DEVELOP` ("review")
outcomes to review.

In the UI, the **Input** tab loads the fixed reference data automatically and lets you
**upload your own change-request workbook** (or use the bundled sample). Clicking
**Process** scores every row and unlocks the **Single decision** and **Batch report**
dashboard tabs.

## Project layout

```
provider-validation/
  app/                       Streamlit UI (imports only from engine/)
    main.py                  entrypoint — Input + Single decision + Batch report tabs
    components/              input_page, selector, trace_viewer, batch_report, theme
    assets/                  Dash mascot + wordmark
  api/                       FastAPI layer (thin adapter, imports only from engine/)
    main.py                  app + lifespan (loads workbook once) + CORS
    deps.py                  Store + get_store dependency
    schemas.py               request/response wrappers around engine models
    routers/                 health, decisions (by-id/inline/batch), reference
  engine/                    deterministic decision core (no UI imports)
    enums.py                 Outcome, ChangeCategory, ChangeAction, ...
    models.py                Pydantic v2: ProviderContract, ChangeRequest, Decision, ...
    config.py                cached YAML config access
    loaders.py               reference + input workbooks -> typed models (+ integrity asserts)
    tag_engine.py            derive(change, contract) -> TagSet  (pure)
    rules.py                 R-001..R-010 pure functions + registry
    rule_engine.py           evaluate applicable rules
    decision_engine.py       decide() — the only place precedence lives
    scoring.py               batch runner + metrics
  config/
    rules.yaml               editable rulebook (scope, failure outcomes, vocabularies)
    outcomes.yaml            controlled vocabulary + default contract actions
  data/                      reference_data.xlsx + contract_change_requests.xlsx (+ master)
  tools/
    build_input_data.py      regenerate the reference/input split (+ dummy review rows)
  tests/                     loaders, rules, decision, regression, REJECT fixtures
```

## How a decision is made

1. **Load & validate** (`loaders.py`): every sheet is coerced into typed models.
   The loader asserts **zero orphan links** (every `linked_provider_contract_id`
   resolves to a contract) and that every label is in the controlled vocabulary.
2. **Tag** (`tag_engine.py`): `derive(change, contract)` computes booleans/enums such
   as `cross_state_pl_add`, `exclusion_or_debarment`, `special_payment_invalid`,
   `specialty_incompatible`, `needs_development`.
3. **Evaluate** (`rule_engine.py`): only the rules whose `applies_to_change_category`
   matches the request (or `All`) fire, each returning a `RuleResult`.
4. **Decide** (`decision_engine.py`): an ordered **precedence ladder** resolves the
   single outcome (first match wins):

   | Tier | Condition | Outcome |
   |---|---|---|
   | 1 | adverse exclusion/debarment (R-005) **or** incompatible specialty (R-009) | `DENY` |
   | 2 | wrong CMS form (R-001) **or** missing signature (R-008) | `REJECT` |
   | 3 | out-of-state practice-location add (R-003) | `INITIAL_ENROLLMENT_REQUIRED` |
   | 4 | any DEVELOP-class rule failed / docs incomplete | `DEVELOP` |
   | 5 | default | `APPROVE` |

   Tier 1 beating tier 2 is verified by a test: an adverse request *also* missing a
   signature still returns `DENY`.

`decide()` never reads the ground-truth label fields — those are used only by
`scoring.py` and the tests.

## REST API

A FastAPI layer (`api/`) exposes the same engine as a thin HTTP adapter — it contains
**no** decision/tag/rule logic, only imports `engine.decision_engine.decide()` and
serializes the result. The reference workbook is loaded **once** at startup
(`DATA_PATH` env var overrides the directory; default = bundled `data/`).

```bash
uvicorn api.main:app --reload
```

| Method & path | Purpose |
|---|---|
| `POST /v1/decisions/by-id` | Decide a stored change request (`{change_request_id}`); 404 if unknown. |
| `POST /v1/decisions/inline` | Decide a caller-supplied `{change, contract}`; 422 on invalid body. |
| `POST /v1/decisions/batch` | Decide `{change_request_ids: [...]}` in order; unknown ids reported per-item. |
| `GET /v1/contracts/{id}` | Read back a contract; 404 if missing. |
| `GET /v1/changes/{id}` | Read back a change request (label fields stripped); 404 if missing. |
| `GET /v1/rules` | The editable rulebook from `config/rules.yaml`. |
| `GET /health` | `{status, contracts, changes, rules}` counts. |

Semantics: **business outcomes (APPROVE/DEVELOP/DENY/REJECT/INITIAL_ENROLLMENT_REQUIRED)
are all `200`** — a denial is a *successful* evaluation. `4xx` is reserved for transport
problems (`404` unknown id, `422` invalid body). Responses never include the ground-truth
`expected_*` label fields. Decisions are deterministic: identical request body →
byte-identical Decision. An optional `X-Correlation-Id` request header is echoed in
response metadata, *outside* the Decision object. Configure CORS with the
`ALLOWED_ORIGINS` env var (comma-separated; default none).

## Results (acceptance)

Running the engine over all labeled requests reproduces every label. The input file
ships with the 60 original rows plus 12 appended dummy `DENY`/`DEVELOP` review rows:

| Outcome | Count |
|---|---|
| APPROVE | 49 |
| DEVELOP | 12 |
| DENY | 10 |
| INITIAL_ENROLLMENT_REQUIRED | 1 |
| REJECT | 0 (rule-driven; tested via synthetic fixtures) |

**72/72 outcome matches.** `REJECT` never appears in the data, so it is exercised with
synthetic wrong-form and missing-signature fixtures (`tests/fixtures_reject.py`).

## Editing the rulebook

`config/rules.yaml` is the editable rulebook. You can retune **without touching code**:

- `rules.<id>.applies_to_change_category` — which requests a rule fires for.
- `rules.<id>.failure_outcome` — the verdict a rule produces on failure.
- `parameters.special_payment_allowed_types` — allowed special-payment destinations (R-004).
- `parameters.exclusion_keywords` — adverse findings that hard-block to DENY (R-005).
- `parameters.incompatible_specialty_targets` — provider-type reclassifications that DENY (R-009).

`config/outcomes.yaml` maps each outcome to its default downstream contract action.

## Notes on data-driven refinements

The build brief's simplified ladder was refined to match the *actual* labeled workbook,
which is richer than "adverse ⇒ DENY":

- **Final Adverse Legal Action splits**: an OIG *exclusion/debarment* hard-blocks to
  `DENY` (R-005); a *license-probation disclosure* with development requested is
  `DEVELOP`.
- **Some `DENY`s are specialty incompatibilities** (`Internal Medicine → Physician
  Assistant`) via R-009, not adverse action.
- **`DEVELOP` correlates with `development_requested = Yes`** / a populated
  `development_response_due_date`, consistent with acceptance criterion AC-4.

The engine reports both outcome accuracy (the acceptance target, 72/72) and a secondary
contract-action comparison; per-row action strings in the dataset are free-text and
granular, so the engine emits a canonical action per outcome from `outcomes.yaml`.
