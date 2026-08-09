# Data Dictionary

Field-level reference for the database entities (SQLAlchemy models in
`backend/app/models.py`) and the CSV import contract.

Conventions: all money values are USD floats; areas are square feet; distances
are miles; timestamps are naive UTC; `condition` uses the ordinal scale
poor < fair < average < good < excellent.

## users

| Field | Type | Notes |
|---|---|---|
| id | int PK | |
| email | str unique | Demo mode seeds `demo@example.com` |
| display_name | str | |
| created_at | datetime | |

## cma_analyses

| Field | Type | Notes |
|---|---|---|
| id | int PK | |
| user_id | FK users | |
| title | str | |
| status | str | `draft` \| `completed` \| `archived` (archive = soft delete) |
| notes | text? | |
| created_at / updated_at | datetime | `updated_at` touched on any child change |

## subject_properties (1:1 with cma_analyses)

| Field | Type | Notes |
|---|---|---|
| address | str | required |
| city, zip_code | str? | |
| latitude, longitude | float? | enables haversine proximity |
| property_type | str | one of `single_family, condo, townhouse, multi_family, manufactured, other` |
| bedrooms | int? | |
| bathrooms | float? | halves allowed (2.5) |
| square_feet | float? | > 0 when present |
| lot_size | float? | |
| year_built | int? | 1800..next year |
| condition | str? | ordinal scale above |
| parking_spaces | int? | |
| has_pool | bool | default false |
| renovation_notes, agent_notes | text? | agent_notes never appears in reports |

## comparable_properties

Same physical fields as the subject, plus:

| Field | Type | Notes |
|---|---|---|
| sale_price | float | required, > 0 |
| sale_date | date | required, not future |
| square_feet, bedrooms, bathrooms | required | unlike subject |
| distance_from_subject | float? | miles; fallback when either side lacks coordinates |
| notes, source | str? | source defaults: `manual-entry` / `csv-upload` |

## comparable_selections (1:1 with comparable_properties)

| Field | Type | Notes |
|---|---|---|
| included | bool | drives reconciliation membership |
| similarity_score | float? | 0–100; null until scored |
| similarity_breakdown | JSON? | full component breakdown (see METHODOLOGY §2) |
| user_weight_multiplier | float | 0–10, default 1.0; the explicit override lever |
| exclusion_reason | text? | audit-logged |

## adjustments

| Field | Type | Notes |
|---|---|---|
| comparable_id | FK | |
| category | str | `market_time, living_area, lot_size, bedrooms, bathrooms, condition, parking, pool` or free-form manual |
| subject_value / comparable_value | str? | display values ("1850 sq ft") |
| unit_description | str? | the math ("300 sq ft × $150/sq ft") |
| amount | float | signed; + adjusts the comparable upward |
| source | str | `suggested` \| `manual` (edits re-flag to manual) |
| explanation | text? | |
| direction | derived | upward / downward / none from sign of amount |

## weight_configurations (1:1 with cma_analyses)

| Field | Type | Notes |
|---|---|---|
| weights | JSON | component → weight (see constants.DEFAULT_WEIGHTS) |
| similarity_params | JSON | curve caps (max distance, tolerances, …) |
| assumptions | JSON | dollar assumptions for suggested adjustments |
| reconciliation | JSON | range_k, warning thresholds |

## valuation_results (append-only history)

| Field | Type | Notes |
|---|---|---|
| calc_version | str | e.g. `calc-v1.0` |
| central_estimate / low_estimate / high_estimate | float? | null when no comps |
| median_adjusted | float? | unweighted median |
| weighted_ppsf | float? | over comps with valid sq ft |
| dispersion | float? | weighted std dev; null for n ≤ 1 |
| cov | float? | dispersion / central |
| included_count | int | |
| warnings | JSON | `[{code, message, comp_id?}]` |
| per_comparable | JSON | weight/influence snapshot per included comp |

## listing_strategies

| Field | Type | Notes |
|---|---|---|
| key | str | `market_entry` \| `competitive` \| `aspirational` |
| list_price | float | editable |
| is_user_modified | bool | preserved across regeneration |
| derived | JSON | pct/dollar vs value, position percentile, interest, risk, notes, caveat |

## audit_events (append-only)

| Field | Type | Notes |
|---|---|---|
| timestamp | datetime | |
| actor | str | `demo` / `seed-script` (auth-ready) |
| event_type | str | ~16 types (`comparable_excluded`, `weight_override`, …) |
| entity_type / entity_id | str?/int? | what was touched |
| summary | text | plain-language sentence shown on the audit screen |
| details | JSON? | before/after values, snapshots |
| calc_version | str | |

## generated_reports

| Field | Type | Notes |
|---|---|---|
| calc_version | str | |
| format | str | `html` \| `pdf` |
| content_html | text | the report itself (self-contained) |
| pdf_path | str? | only when WeasyPrint produced a PDF |

## CSV import contract

Header names must match exactly (case-insensitive). Required:
`address, sale_price, sale_date, square_feet, bedrooms, bathrooms`.
Validation per row: price > 0; date `YYYY-MM-DD` or `MM/DD/YYYY`, not future;
sq ft > 0; bedrooms whole ≥ 0; bathrooms ≥ 0; lat ∈ [−90, 90]; lon ∈ [−180, 180];
year_built ∈ [1800, next year]; condition/property_type from their enums; pool
∈ {true,false,yes,no,y,n,1,0,blank}; currency symbols/commas stripped from
numbers. Limits: 2 MB, 500 rows. Failed rows are reported as
`{row, field, message}` and skipped; valid rows import.
