# Changelog

## v0.1.0 — 2026-08-08

First release: the complete transparent-CMA MVP.

### Added

- **CMA engine (calc-v1.0)** — nine-component similarity scoring with stored
  breakdowns and missing-data renormalization; assumption-driven adjustment
  suggestions with the standard direction convention and visible unit math;
  weighted reconciliation (normalized weights, weighted std-dev range,
  gross/net adjustment percentages) with seven explicit warning conditions;
  deterministic listing-strategy heuristics with documented thresholds.
- **API** — 24 documented endpoints (OpenAPI at `/docs`): CMA CRUD, subject,
  comparables (manual + CSV with row-level errors), selection/overrides,
  similarity, adjustments, valuation, strategies, audit trail, reports,
  CSV template, config, meta.
- **Frontend** — dashboard plus a seven-step workflow (subject, comparables,
  adjustments, valuation, strategies, report, audit) with sortable/filterable
  tables, similarity breakdown explorer, editable adjustment grid, influence
  table, Recharts valuation chart with table equivalent, and accessible
  loading/empty/validation/error states.
- **Reporting** — server-rendered, print-ready seller report (HTML; PDF when
  WeasyPrint is installed) with methodology, adjustment grids, reconciliation,
  strategies, assumptions, and disclaimer.
- **Auditability** — append-only audit trail with plain-language summaries,
  before/after details, and calculation-version stamps on every event,
  valuation, and report.
- **Data** — synthetic San Gabriel Valley sample set (20 comps), CSV template,
  idempotent demo seed script.
- **Quality** — 79 backend tests, 18 frontend component tests, 2 Playwright
  e2e journeys; Ruff/ESLint/strict TS; GitHub Actions CI (backend, frontend,
  e2e); Dependabot; issue/PR templates.

### Known limitations

See README *Limitations* — educational tool, sample assumptions, no auth/rate
limiting (do not deploy publicly as-is), no live market data.
