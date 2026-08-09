# CMA Decision Platform

A transparent Comparative Market Analysis (CMA) and listing-strategy platform for
residential real-estate agents: every number is explainable, every override is
audited, and nothing is a black box.

![Valuation screen: value range, dispersion, warnings, and per-comparable influence](screenshots/valuation.png)

> **Disclaimer.** This is an open-source portfolio and educational project. It is
> **not** an appraisal tool, its outputs are informational analytical estimates
> built from user-reviewed sample assumptions, and any real decision should be
> reviewed with a qualified real-estate professional. All bundled data is
> synthetic.

## The problem

Agents preparing a listing presentation need to justify a price to a seller.
Generic "AI value" tools produce a number without showing the work, which is
useless in that conversation (and dangerous if trusted). A CMA is fundamentally
an argument built from evidence (comparable sales, documented adjustments, and
judgment), and the tooling should make that argument inspectable, not hide it.

## Key features

- **Subject property & comparables**: manual entry or CSV upload with
  row-level validation errors (bad rows rejected individually; good rows import).
- **Transparent similarity scoring**: nine weighted components (proximity,
  living area, type, recency, beds, lot, baths, age, condition), each shown with
  its raw values, curve math, weight, and contribution. Missing data is skipped
  and renormalized, never guessed.
- **Editable adjustment grid**: suggested adjustments computed from per-analysis
  assumptions with the unit math shown (`300 sq ft × $150/sq ft`); standard
  direction convention (inferior comp ⇒ upward); every edit becomes a flagged
  manual override.
- **Reconciliation with uncertainty**: weighted central estimate, median,
  weighted $/sq ft, dispersion-based low–high range, per-comparable influence
  percentages, and explicit warnings (too few comps, outliers, stale sales,
  over-adjusted comps, high dispersion).
- **Assumption sensitivity**: a tornado view of how much the central estimate
  moves as each assumption varies ±20%, so users see exactly which inputs the
  result leans on.
- **Proximity map**: dependency-free SVG plot of comps around the subject with
  distance rings (no external tile servers or scraping).
- **Listing strategy simulator**: Market-Entry / Competitive / Aspirational
  scenarios with editable prices and deterministic, documented heuristics for
  buyer-interest and price-reduction-risk labels (no fake DOM predictions).
- **Seller-facing report**: print-ready document with methodology, comparables,
  adjustment grids, reconciliation, strategies, assumptions, and disclaimer.
  PDF via WeasyPrint when installed; print-optimized HTML otherwise.
- **Audit trail**: append-only, plain-language log of every inclusion decision,
  weight change, assumption change, override, recalculation, and report, each
  stamped with the calculation version.

| Comparables & similarity | Strategies | Audit trail |
|---|---|---|
| ![Comparables table](screenshots/comparables.png) | ![Strategy comparison](screenshots/strategies.png) | ![Audit trail](screenshots/audit-trail.png) |

## Methodology in one paragraph

Comparables are scored 0–100 for similarity with configurable component weights;
each comparable's sale price is adjusted for measurable differences from the
subject using per-analysis dollar assumptions; adjusted values are reconciled
with `normalized_weight_i = raw_weight_i / Σ raw_weights` and
`central = Σ (adjusted_i × weight_i)`; the range is `central ± k × weighted std
dev` and is labeled an analytical estimate, not a confidence interval. The full
specification with worked examples is in
[docs/METHODOLOGY.md](docs/METHODOLOGY.md): the unit tests enforce it.

## Architecture

```mermaid
flowchart LR
    subgraph Frontend [Next.js 14 + TypeScript + Tailwind]
        UI[Workflow UI<br>dashboard → subject → comps →<br>adjustments → valuation →<br>strategies → report → audit]
    end
    subgraph Backend [FastAPI]
        API[Routers<br>validation + persistence + audit]
        SVC[Domain services<br>similarity · adjustments ·<br>reconciliation · strategies ·<br>csv · report]
        API --> SVC
    end
    DB[(SQLite default /<br>PostgreSQL optional<br>SQLAlchemy 2 + Alembic)]
    UI -->|JSON /api| API
    API --> DB
```

All calculation logic lives in pure, unit-tested functions under
`backend/app/services/`: route handlers only validate, persist, and audit-log.
See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Technology stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Recharts |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2, Alembic |
| Database | SQLite by default; PostgreSQL 16 via `docker-compose` |
| Testing | pytest (112 tests) · Vitest + React Testing Library (33) · Playwright e2e (2 journeys × 2 engines) |
| Quality | Ruff, ESLint, TypeScript strict, GitHub Actions CI |
| Reports | Jinja2 → print-ready HTML (→ PDF when WeasyPrint is installed) |

## Local setup

Prerequisites: **Python ≥ 3.9** and **Node ≥ 20**. No database server needed
(SQLite is the default).

```bash
git clone <your-fork-url> cma-decision-platform
cd cma-decision-platform
```

**Backend** (terminal 1):

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head          # create the schema (SQLite file: backend/cma.db)
python -m app.seed            # optional: seed the synthetic demo CMA
uvicorn app.main:app --reload --port 8000
```

**Frontend** (terminal 2):

```bash
cd frontend
npm install
npm run dev                   # http://localhost:3000
```

API docs (OpenAPI/Swagger): http://localhost:8000/docs

### Environment variables

Copy `.env.example` to `.env` (all optional for local dev):

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./cma.db` | SQLAlchemy URL; set to Postgres for parity |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |
| `NEXT_PUBLIC_API_BASE` | `http://localhost:8000` | API base URL baked into the frontend at build time |

Note: `NEXT_PUBLIC_API_BASE` is read by **Next.js**, not the backend, so a root
`.env` does not reach it. To change it, put it in `frontend/.env.local` (or
export it in the shell that runs `npm run dev` / `npm run build`).

### PostgreSQL option

```bash
docker compose up -d db
export DATABASE_URL=postgresql+psycopg2://cma:cma_dev_password@localhost:5432/cma
pip install psycopg2-binary
alembic upgrade head && python -m app.seed
```

## Running tests

```bash
# Backend unit + API tests
cd backend && source .venv/bin/activate && pytest

# Lint
ruff check app tests

# Frontend component tests / lint / types
cd frontend && npm test && npm run lint && npm run typecheck

# End-to-end (browsers: npx playwright install chromium webkit).
# Locally, Playwright reuses servers already running on :3000/:8000 - including
# their database - so e2e test CMAs will appear in that database. For an
# isolated run (build first; Playwright's `npm run start` does not build):
#   cd frontend && npm run build
#   CI=1 npx playwright test        # starts its own servers on a scratch DB
cd frontend && npx playwright test

# Independent math audit: recomputes the entire seeded valuation from the
# METHODOLOGY formulas (no app code imported) and compares against the API
python3 tools/verify_math.py
```

## CSV format

Download the template from the app (or `data/sample/comparables_template.csv`).
Required columns: `address`, `sale_price`, `sale_date` (YYYY-MM-DD),
`square_feet`, `bedrooms`, `bathrooms`. Optional: `city`, `zip_code`,
`latitude`, `longitude`, `property_type`, `lot_size`, `year_built`, `condition`
(poor/fair/average/good/excellent), `parking_spaces`, `pool` (true/false),
`distance_from_subject` (miles), `notes`, `source`. Full details:
[data/sample/README.md](data/sample/README.md) and
[docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md).

## Example workflow

1. **Dashboard** → *Create new CMA* (or open the seeded demo).
2. **Subject**: enter the property (address required; more data → more
   computable components).
3. **Comparables**: upload the sample CSV; *Recalculate similarity*; click any
   score to see its component breakdown; exclude weak comps with a reason.
4. **Adjustments**: review the sample assumptions, *Generate suggested
   adjustments*, edit any amount (it becomes a flagged manual override), add
   manual line items.
5. **Valuation**: *Calculate valuation*; read the range, warnings, and each
   comparable's influence percentage.
6. **Strategies**: generate the three scenarios; edit prices to compare.
7. **Report**: generate and print/save the seller-facing document.
8. **Audit trail**: the full, timestamped story of every number.

## Data & privacy policy

- Bundled data is **synthetic**: fabricated addresses, invented prices.
- The intended data paths are manual entry, user-supplied CSVs, and public
  datasets whose terms permit the use. The project does **not** scrape Zillow,
  Redfin, Realtor.com, or MLS systems, and contributions that bypass terms of
  service, authentication, or rate limits are not accepted.
- Never commit real client records, private addresses tied to clients, MLS
  credentials, or brokerage-confidential data. See [docs/SECURITY.md](docs/SECURITY.md).

## Known limitations

- Educational tool; not USPAP-compliant; not an appraisal.
- Linear similarity curves and additive dollar adjustments are simplifications;
  they are documented and independently verified, not empirically validated
  against market outcomes.
- Default weights/assumptions are demonstration values requiring user review.
  The arithmetic is provably correct (`tools/verify_math.py`), but the outputs
  are only as good as the assumptions a user feeds in.
- **No authentication, authorization, or rate limiting**: run it locally or
  behind your own auth. Do not deploy it publicly with real client data as-is.
- Licensed comparable-data acquisition (MLS, county records) is out of scope;
  the data path is manual entry and user-supplied CSVs.
- No live market data, geocoding, or map tiles in the MVP.
- Demo mode is single-user with a seeded account (schema is auth-ready).
- Strategy labels are deterministic heuristics, not validated predictions.
- The valuation range is an analytical band (weighted std dev), not a
  statistical confidence interval.
- Reports are gated on consistency (stale valuations are refused), but a
  polished report can still convey more confidence than sample assumptions
  deserve; the disclaimer and assumption tables exist for exactly that reason.

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md). Next up: paired-sales analysis to
*derive* adjustment suggestions from the comp set itself, a real map view, and
authentication for multi-user deployments.

## Contributing

PRs welcome; read [CONTRIBUTING.md](CONTRIBUTING.md). The one hard rule: every
user-visible number must remain explainable (breakdown, unit math, or audit
event). Calculation changes must bump `CALC_VERSION` and update
[docs/METHODOLOGY.md](docs/METHODOLOGY.md) in the same PR.

## License

[MIT](LICENSE).
