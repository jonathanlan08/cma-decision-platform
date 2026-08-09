# Changelog

## Unreleased

- **Outdated-data visibility everywhere** (UX review follow-up, 2026-08-09):
  - The dashboard shows an "outdated: recalculate" badge on any analysis
    whose value range no longer matches its inputs.
  - The strategies screen warns when its cards were generated from an
    earlier valuation (via the stored valuation_id) with an inline
    refresh action.
  - The comparables table collapses secondary columns (sale date, sq ft,
    beds/baths, distance) on phones; the sold date moves into the address
    sub-line and full details stay in the expandable breakdown.

- **Convenience & accessibility pass** (2026-08-09):
  - Failed form submits move focus to the first invalid field (subject and
    comparable forms).
  - Checkbox touch targets enlarged to a 44px hit area (include toggles,
    pool checkbox).
  - Strategy price inputs show currency formatting ($ prefix, thousands
    separators) and accept pasted "$1,234,567" values.
  - The stale-valuation banner gained a one-click "Recalculate valuation &
    refresh strategies" repair button.
  - The workflow stepper auto-centers the active step on narrow screens and
    shows an edge fade so later steps are never silently hidden (scrolling
    only its own container, never the page).
  - Analyses can be renamed inline from the workflow header (audit-logged).

- **Provenance and completeness hardening** (second external audit round,
  2026-08-09):
  - Suggested adjustments record the assumption set that produced them.
    Changing assumptions without regenerating flags the config
    (`suggestions_outdated`), adds an `outdated_suggestions` warning to any
    valuation computed from them, shows a banner on the adjustments screen,
    and blocks report generation (409) until suggestions are regenerated.
  - Reports now require a complete chain: no valuation or no strategies
    returns 400 instead of producing a seller-facing document with empty
    sections; the Generate button explains what is missing.
  - Hard input bounds: adjustment amounts ±$1B, sale/list prices ≤ $1B,
    living area ≤ 1M sq ft, lot ≤ 100M sq ft (API and CSV), so extreme but
    "valid" numbers can no longer overflow into Infinity. A non-positive
    central estimate gets a `nonpositive_estimate` warning and blocks
    strategy generation (previously a negative central could generate
    negative list prices).
  - Manual comparable entry no longer guesses: property type and pool
    default to "Not specified" (stored as unknown) instead of
    single-family/no-pool.
  - Freshness now updates onscreen immediately: weight, multiplier, and
    adjustment changes refresh the header staleness flag without a reload,
    and each strategy records the `valuation_id` it was derived from
    (shown on the strategy cards).
  - 6 new backend regression tests (112 pytest total); fixtures updated.

- **Integrity hardening (calc-v1.1)**, responding to an external audit
  (2026-08-08):
  - Staleness detection: every valuation stores a SHA-256 fingerprint of its
    inputs; the API flags stale valuations, the UI shows "inputs changed"
    warnings, and report generation returns 409 until the valuation and
    strategies are refreshed from one consistent state.
  - Unscored comparables (no similarity score) now carry zero weight in
    reconciliation with an explicit warning; previously they were silently
    given full base weight and could outrank scored comparables.
  - Adequacy warnings and the single-comparable band use the new
    `effective_count` (comparables with positive weight), so weights like
    [1, 0, 0] no longer produce a zero-width range with no warning.
  - Configuration updates are strictly validated: unknown keys, NaN/Infinity,
    negative `range_k`, negative dollar assumptions, and non-positive
    similarity caps are rejected with 422.
  - CSV import rejects NaN/Infinity values and surplus cells as row-level
    errors (previously they could 500 or corrupt the analysis), and blank
    `property_type`/`pool` are stored as unknown (null) instead of being
    guessed as `single_family`/`false`; unknown values are skipped in scoring
    and adjustments, matching the "missing data is never guessed" promise.
  - Explicit JSON `null` on required PATCH fields returns 422 instead of 500;
    comparable PATCH now enforces the future-sale-date rule; no-op adjustment
    PATCHes no longer create misleading audit events.
  - Frontend failure recovery: generating suggestions saves visible (unsaved)
    assumption edits first; failed saves no longer clear form drafts or leave
    controls permanently disabled; report generation no longer relies on a
    blockable popup and updates the workflow stepper immediately; the
    dashboard gained complete/archive/restore controls; the weights editor
    blocks an all-zero total.
  - Hardening: SQLite foreign-key enforcement enabled, audit pagination moved
    into SQL, upload size checked before reading, report favicon 404 fixed,
    `tools/verify_math.py` no longer assumes CMA id 1 and verifies the new
    semantics. 24 new regression tests (19 backend, 5 frontend); suite totals
    are now 106 pytest + 33 Vitest.

- Full QA pass (see docs/QA_REPORT.md): fixed a UTC date-shift display bug,
  replaced `window.confirm` deletion with an accessible two-step confirm,
  made Enter commit strategy prices directly, plus two cosmetic fixes.
  E2E now also runs on WebKit (Safari/iOS engine) locally and in CI.
- "How to use" guide page (`/guide`): workflow walkthrough, CSV help,
  glossary, FAQ, data rules, linked from the header and dashboard.
- Assumption sensitivity analysis: `GET /api/cmas/{id}/sensitivity` varies
  each assumption ±20% (manual adjustments held fixed) and the valuation
  screen shows a tornado panel of the impacts, sorted largest first.
- Proximity map on the comparables screen: dependency-free SVG plot of
  comparables around the subject with distance rings and included/excluded
  encoding.
- UI polish: IBM Plex Sans (self-hosted), progress-aware workflow stepper
  (summary API now exposes `strategy_count`/`report_count`), dashboard stat
  row, unified low–central–high range panel (mobile-safe), SVG warning icons,
  `prefers-reduced-motion` support, contrast fixes.

## v0.1.0 (2026-08-08)

First release: the complete transparent-CMA MVP.

### Added

- **CMA engine (calc-v1.0)**: nine-component similarity scoring with stored
  breakdowns and missing-data renormalization; assumption-driven adjustment
  suggestions with the standard direction convention and visible unit math;
  weighted reconciliation (normalized weights, weighted std-dev range,
  gross/net adjustment percentages) with seven explicit warning conditions;
  deterministic listing-strategy heuristics with documented thresholds.
- **API**: 24 documented endpoints (OpenAPI at `/docs`): CMA CRUD, subject,
  comparables (manual + CSV with row-level errors), selection/overrides,
  similarity, adjustments, valuation, strategies, audit trail, reports,
  CSV template, config, meta.
- **Frontend**: dashboard plus a seven-step workflow (subject, comparables,
  adjustments, valuation, strategies, report, audit) with sortable/filterable
  tables, similarity breakdown explorer, editable adjustment grid, influence
  table, Recharts valuation chart with table equivalent, and accessible
  loading/empty/validation/error states.
- **Reporting**: server-rendered, print-ready seller report (HTML; PDF when
  WeasyPrint is installed) with methodology, adjustment grids, reconciliation,
  strategies, assumptions, and disclaimer.
- **Auditability**: append-only audit trail with plain-language summaries,
  before/after details, and calculation-version stamps on every event,
  valuation, and report.
- **Data**: synthetic San Gabriel Valley sample set (20 comps), CSV template,
  idempotent demo seed script.
- **Quality**: 79 backend tests, 18 frontend component tests, 2 Playwright
  e2e journeys; Ruff/ESLint/strict TS; GitHub Actions CI (backend, frontend,
  e2e); Dependabot; issue/PR templates.

### Known limitations

See README *Limitations*: educational tool, sample assumptions, no auth/rate
limiting (do not deploy publicly as-is), no live market data.
