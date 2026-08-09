# Roadmap

## v0.1.0 (current) — Transparent CMA MVP

Complete workflow: subject → comparables (CSV/manual) → similarity →
adjustments → reconciliation → strategies → report → audit trail, with the full
test pyramid and CI. SQLite default, Postgres option, no auth (demo mode).

## v0.2 — Evidence-derived adjustments

- **Paired-sales analysis**: derive suggested adjustment magnitudes from the
  comparable set itself (e.g., regress adjusted price on GLA within the comp
  set) and show the derivation — keeping the transparency rule.
- Sensitivity view: how the range moves as each assumption varies.
- Assumption presets per market area, still user-owned and audited.

## v0.3 — Map & market context

- Map view of subject + comps (Leaflet/MapLibre with open tiles).
- Optional public-dataset import adapters where licensing allows, with
  provenance recorded per row.
- Market-trend helper for the time adjustment (user-confirmed, never silent).

## v0.4 — Multi-user

- Authentication (the `User` FK exists everywhere already) and per-user data.
- Team review flow: a second agent can annotate an analysis before the listing
  appointment (annotations land in the audit trail).
- Postgres as the documented production default; managed deployment recipe.

## v0.5 — Presentation polish

- Branded report themes and a client-friendly share link (read-only).
- Plain-language AI explanations of the deterministic results — explicitly
  scoped so AI narrates stored numbers and never invents data or conclusions.
- Spanish/Chinese report localization (relevant to the San Gabriel Valley).

## Explicit non-goals

- Automated valuation without explainability (black-box AVM).
- Scraping Zillow/Redfin/Realtor/MLS or bypassing any terms of service.
- Claiming appraisal compliance, DOM predictions, or accuracy figures without
  measured evidence.
