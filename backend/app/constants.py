"""Central constants for the CMA calculation engine.

CALC_VERSION is stamped on every stored valuation, report, and audit event so
the audit trail always records which version of the methodology produced a
number. Bump it whenever calculation behavior changes.
"""

CALC_VERSION = "calc-v1.0"

DISCLAIMER = (
    "This Comparative Market Analysis is an informational estimate produced by an "
    "educational, open-source tool. It is not an appraisal, is not prepared by a "
    "licensed appraiser, and must not be relied on for lending or legal purposes. "
    "All assumptions are user-reviewable sample values, not market standards. "
    "Review with a qualified real-estate professional before making decisions."
)

# Ordinal condition scale (1 = worst). Used for similarity and condition adjustments.
CONDITION_SCALE = ["poor", "fair", "average", "good", "excellent"]

PROPERTY_TYPES = [
    "single_family",
    "condo",
    "townhouse",
    "multi_family",
    "manufactured",
    "other",
]

CMA_STATUSES = ["draft", "completed", "archived"]

# --- Default similarity component weights -----------------------------------
# Stored per-CMA and fully editable. These are demonstration defaults chosen to
# emphasize location, size, and property type; they are NOT universal appraisal
# standards (see docs/METHODOLOGY.md).
DEFAULT_WEIGHTS = {
    "proximity": 0.20,
    "living_area": 0.20,
    "property_type": 0.15,
    "recency": 0.10,
    "bedrooms": 0.08,
    "lot_size": 0.08,
    "bathrooms": 0.07,
    "age": 0.07,
    "condition": 0.05,
}

# Parameters that shape each similarity component's 0-100 curve.
DEFAULT_SIMILARITY_PARAMS = {
    "max_distance_miles": 3.0,
    "living_area_tolerance": 0.30,   # fraction of subject living area
    "lot_size_tolerance": 0.50,      # fraction of subject lot size
    "bedroom_cap": 3,                # difference at which score reaches 0
    "bathroom_cap": 3,
    "age_cap_years": 30,
    "recency_cap_months": 12,
    "condition_cap_steps": 4,
}

# --- Default adjustment assumptions -----------------------------------------
# Demonstration values only, clearly labeled in the UI and report as sample
# assumptions requiring user review. Stored per-CMA and editable.
DEFAULT_ASSUMPTIONS = {
    "monthly_market_pct": 0.003,     # 0.3%/month market movement
    "gla_per_sqft": 150.0,           # $ per sq ft of living-area difference
    "lot_per_sqft": 5.0,             # $ per sq ft of lot-size difference
    "per_bedroom": 10000.0,
    "per_bathroom": 12500.0,
    "per_condition_step": 15000.0,
    "per_parking_space": 7500.0,
    "pool_value": 25000.0,
}

# --- Reconciliation parameters ----------------------------------------------
DEFAULT_RECONCILIATION = {
    "range_k": 1.0,                  # low/high = central -/+ k * weighted std dev
    "single_comp_range_pct": 0.05,   # fallback range when only one comp is included
    "high_dispersion_cov": 0.15,     # warn when coefficient of variation exceeds this
    "gross_adjustment_warn_pct": 0.25,  # warn when |adjustments| exceed 25% of price
    "stale_sale_months": 12,         # warn on included sales older than this
    "outlier_deviation_pct": 0.20,   # warn when adjusted value deviates >20% from median
}

# --- Listing strategy heuristics --------------------------------------------
# Deterministic scenario heuristics (NOT validated predictions; see METHODOLOGY.md).
STRATEGY_DEFAULTS = [
    {
        "key": "market_entry",
        "name": "Market-Entry",
        "pct_of_value": 0.97,
        "description": "List slightly below the indicated value to maximize early "
        "buyer traffic and the chance of competing offers.",
    },
    {
        "key": "competitive",
        "name": "Competitive",
        "pct_of_value": 1.00,
        "description": "List at the indicated market value to balance exposure "
        "and negotiating room.",
    },
    {
        "key": "aspirational",
        "name": "Aspirational",
        "pct_of_value": 1.05,
        "description": "List above the indicated value to test the ceiling, "
        "accepting longer expected market time and price-reduction risk.",
    },
]

# Thresholds (as fraction above/below central estimate) for qualitative labels.
STRATEGY_INTEREST_THRESHOLDS = {"high_below": -0.02, "low_above": 0.03}
STRATEGY_RISK_THRESHOLDS = {"low_below": 0.0, "high_above": 0.05}

CSV_MAX_BYTES = 2 * 1024 * 1024  # 2 MB
CSV_MAX_ROWS = 500

CSV_COLUMNS = [
    "address",
    "city",
    "zip_code",
    "latitude",
    "longitude",
    "property_type",
    "sale_price",
    "sale_date",
    "square_feet",
    "lot_size",
    "bedrooms",
    "bathrooms",
    "year_built",
    "condition",
    "parking_spaces",
    "pool",
    "distance_from_subject",
    "notes",
    "source",
]

CSV_REQUIRED_COLUMNS = [
    "address",
    "sale_price",
    "sale_date",
    "square_feet",
    "bedrooms",
    "bathrooms",
]
