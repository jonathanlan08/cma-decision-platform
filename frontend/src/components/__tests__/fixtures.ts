import type { Adjustment, Comparable, Strategy } from "@/lib/types";

export function makeAdjustment(overrides: Partial<Adjustment> = {}): Adjustment {
  return {
    id: 1,
    category: "living_area",
    subject_value: "2000 sq ft",
    comparable_value: "1700 sq ft",
    unit_description: "300 sq ft × $150/sq ft",
    amount: 45000,
    direction: "upward",
    source: "suggested",
    explanation: "Comparable is 300 sq ft smaller than the subject.",
    updated_at: "2026-08-01T12:00:00",
    ...overrides,
  };
}

export function makeComparable(overrides: Partial<Comparable> = {}): Comparable {
  return {
    id: 1,
    address: "1210 Demo Oak Ave",
    city: "Arcadia",
    zip_code: "91006",
    latitude: null,
    longitude: null,
    property_type: "single_family",
    sale_price: 1285000,
    sale_date: "2026-06-12",
    square_feet: 1820,
    lot_size: 7100,
    bedrooms: 3,
    bathrooms: 2,
    year_built: 1956,
    condition: "good",
    parking_spaces: 2,
    has_pool: false,
    distance_from_subject: 0.4,
    notes: null,
    source: "synthetic-demo",
    selection: {
      included: true,
      similarity_score: 91.5,
      similarity_breakdown: null,
      user_weight_multiplier: 1,
      exclusion_reason: null,
    },
    adjustments: [],
    effective_distance_miles: 0.4,
    adjusted_price: 1285000,
    adjusted_ppsf: 706.04,
    gross_adjustment_pct: 0,
    net_adjustment_pct: 0,
    ...overrides,
  };
}

export function makeStrategy(overrides: Partial<Strategy> = {}): Strategy {
  return {
    id: 1,
    key: "competitive",
    name: "Competitive",
    list_price: 1000000,
    is_user_modified: false,
    derived: {
      pct_vs_value: 0,
      dollar_vs_value: 0,
      position_percentile: 50,
      buyer_interest: "Moderate",
      price_reduction_risk: "Low",
      marketing_notes: "Positioned at market.",
      assumptions: "Scenario estimate from documented heuristics.",
      description: "List at the indicated market value.",
    },
    updated_at: "2026-08-01T12:00:00",
    ...overrides,
  };
}
