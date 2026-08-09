# Implementation Plan: CMA Decision Platform

Written before implementation began (2026-08-08). This document records the plan,
the defaults chosen, and why. See `ROADMAP.md` for what comes after v0.1.0.

## Goal

A transparent Comparative Market Analysis (CMA) and listing-strategy platform for
residential agents, initially oriented to Los Angeles County / San Gabriel Valley.
Portfolio and educational project, **not** a licensed appraisal product. Every
number must be explainable: no black-box valuation, no AI-invented data.

## Architecture

Monorepo:

```
cma-decision-platform/
├── backend/     FastAPI + SQLAlchemy 2 + Alembic; domain services own all math
├── frontend/    Next.js 14 (App Router) + TypeScript + Tailwind + Recharts
├── data/sample/ Synthetic demo comparables + CSV template
├── docs/        Methodology, architecture, data dictionary, roadmap, security
├── .github/     CI, issue/PR templates, dependabot
└── docker-compose.yml  Optional local PostgreSQL
```

Calculation logic lives in `backend/app/services/` (pure, unit-tested functions),
never in route handlers. Routers do validation, persistence, and audit logging.

## Defaults chosen (and why)

| Decision | Default | Rationale |
|---|---|---|
| Database | SQLite via `DATABASE_URL`, Postgres via docker-compose | Runs from a clean clone with zero external services; SQLAlchemy/Alembic keep Postgres a config change away |
| Auth | No-auth demo mode with a seeded demo user row | Spec allows demo mode; `User` entity exists so real auth can be added without schema changes |
| PDF | Server-side Jinja2 HTML report with print CSS; WeasyPrint used when importable, otherwise the HTML itself is the export (browser print-to-PDF) | WeasyPrint needs native libs (Pango) not guaranteed on dev machines; the HTML report is deterministic and CI-testable |
| Similarity weights | Stored per-CMA in `WeightConfiguration`, editable; defaults documented in METHODOLOGY.md | Spec: defaults must not be presented as universal standards |
| Adjustment assumptions | Stored per-CMA, editable, labeled "sample assumptions, review required" | Same transparency requirement |
| Value range | Central ± k × weighted std dev (k default 1.0, configurable), labeled analytical estimate | Simple, explainable, not claimed as a statistical confidence interval |
| Recency in weighting | Recency is a similarity component; reconciliation weight = similarity × user multiplier | One transparent number chain instead of two overlapping recency terms |
| Calc versioning | `CALC_VERSION` constant stamped on every valuation + audit event | Audit trail requirement |

## Phases

1. **Foundation**: repo scaffold, env, schema + migration, seed, sample data, plan/methodology docs.
2. **CMA engine**: similarity, adjustments, reconciliation, strategies, CSV import, audit; pytest suite for all edge cases (no comps, one comp, zero sqft, outliers, overrides, CSV errors).
3. **Product interface**: dashboard + stepper workflow (subject → comparables → adjustments → valuation → strategies → report → audit); accessible tables, charts, loading/empty/error states; Vitest tests.
4. **Reporting & auditability**: server-generated report, audit screen, methodology explanations in the UI.
5. **Release quality**: Playwright e2e, GitHub Actions CI, README + docs, templates, screenshots, secret check, v0.1.0 notes. No remote push without owner authorization.

Each phase is verified (tests/build green) before the next begins.

## Non-goals for v0.1.0

- Live MLS/Zillow/Redfin data (licensing/ToS); CSV upload and manual entry only
- Real geocoding or map tiles (map placeholder; lat/lon supported in data model)
- Regression-based adjustment estimation (documented as roadmap)
- Multi-user auth (schema-ready, not implemented)
