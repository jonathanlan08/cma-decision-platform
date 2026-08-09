// Mirrors backend/app/schemas.py

export type CMAStatus = "draft" | "completed" | "archived";

export interface Valuation {
  id: number;
  calc_version: string;
  created_at: string;
  central_estimate: number | null;
  low_estimate: number | null;
  high_estimate: number | null;
  median_adjusted: number | null;
  weighted_ppsf: number | null;
  dispersion: number | null;
  cov: number | null;
  included_count: number;
  effective_count: number | null;
  warnings: ValuationWarning[] | null;
  per_comparable: PerComparableWeight[] | null;
  // True when inputs changed after this valuation was calculated; null when
  // unknown (valuations stored before fingerprinting).
  stale: boolean | null;
}

export interface ValuationWarning {
  code: string;
  message: string;
  comp_id?: number;
}

export interface PerComparableWeight {
  comp_id: number;
  address: string | null;
  adjusted_price: number;
  similarity: number | null;
  multiplier: number;
  raw_weight: number;
  normalized_weight: number;
  influence_pct: number;
}

export interface Subject {
  id?: number;
  address: string;
  city: string | null;
  zip_code: string | null;
  latitude: number | null;
  longitude: number | null;
  property_type: string;
  bedrooms: number | null;
  bathrooms: number | null;
  square_feet: number | null;
  lot_size: number | null;
  year_built: number | null;
  condition: string | null;
  parking_spaces: number | null;
  has_pool: boolean;
  renovation_notes: string | null;
  agent_notes: string | null;
}

export interface CMASummary {
  id: number;
  title: string;
  status: CMAStatus;
  created_at: string;
  updated_at: string;
  subject_address: string | null;
  comparable_count: number;
  included_count: number;
  strategy_count: number;
  report_count: number;
  latest_valuation: Valuation | null;
}

export interface CMADetail extends CMASummary {
  notes: string | null;
  subject: Subject | null;
}

export interface SimilarityComponent {
  name: string;
  weight: number;
  missing: boolean;
  score: number | null;
  effective_weight: number;
  contribution: number;
  detail: string | null;
  subject_value?: string | null;
  comparable_value?: string | null;
}

export interface SimilarityBreakdown {
  score: number | null;
  as_of: string;
  components: SimilarityComponent[];
  missing_components: string[];
}

export interface Selection {
  included: boolean;
  similarity_score: number | null;
  similarity_breakdown: SimilarityBreakdown | null;
  user_weight_multiplier: number;
  exclusion_reason: string | null;
}

export interface Adjustment {
  id: number;
  category: string;
  subject_value: string | null;
  comparable_value: string | null;
  unit_description: string | null;
  amount: number;
  direction: "upward" | "downward" | "none";
  source: "suggested" | "manual";
  explanation: string | null;
  updated_at: string;
}

export interface Comparable {
  id: number;
  address: string;
  city: string | null;
  zip_code: string | null;
  latitude: number | null;
  longitude: number | null;
  property_type: string | null;
  sale_price: number;
  sale_date: string;
  square_feet: number;
  lot_size: number | null;
  bedrooms: number;
  bathrooms: number;
  year_built: number | null;
  condition: string | null;
  parking_spaces: number | null;
  has_pool: boolean | null;
  distance_from_subject: number | null;
  notes: string | null;
  source: string | null;
  selection: Selection | null;
  adjustments: Adjustment[];
  effective_distance_miles: number | null;
  adjusted_price: number | null;
  adjusted_ppsf: number | null;
  gross_adjustment_pct: number | null;
  net_adjustment_pct: number | null;
}

export interface CSVImportResult {
  imported_count: number;
  error_count: number;
  comparables: Comparable[];
  errors: { row: number; field: string; message: string }[];
}

export interface StrategyDerived {
  pct_vs_value: number;
  dollar_vs_value: number;
  position_percentile: number | null;
  buyer_interest: "High" | "Moderate" | "Low";
  price_reduction_risk: "High" | "Moderate" | "Low";
  marketing_notes: string;
  assumptions: string;
  description?: string;
}

export interface Strategy {
  id: number;
  key: string;
  name: string;
  list_price: number;
  is_user_modified: boolean;
  // The valuation these derived metrics were computed against (provenance).
  valuation_id: number | null;
  derived: StrategyDerived;
  updated_at: string;
}

export interface AuditEvent {
  id: number;
  timestamp: string;
  actor: string;
  event_type: string;
  entity_type: string | null;
  entity_id: number | null;
  summary: string;
  details: Record<string, unknown> | null;
  calc_version: string;
}

export interface SensitivityItem {
  assumption: string;
  value: number;
  low_value: number;
  high_value: number;
  central_low: number | null;
  central_high: number | null;
  delta_low: number | null;
  delta_high: number | null;
}

export interface Sensitivity {
  baseline_central: number | null;
  variation_pct: number;
  note: string;
  items: SensitivityItem[];
}

export interface Config {
  weights: Record<string, number>;
  similarity_params: Record<string, number>;
  assumptions: Record<string, number>;
  reconciliation: Record<string, number>;
  updated_at: string;
  // True when stored suggested adjustments were generated from an assumption
  // set that has since changed; null when unknown.
  suggestions_outdated: boolean | null;
}

export interface Report {
  id: number;
  created_at: string;
  calc_version: string;
  format: "html" | "pdf";
}

export interface Meta {
  calc_version: string;
  disclaimer: string;
  condition_scale: string[];
  property_types: string[];
  default_weights: Record<string, number>;
  default_similarity_params: Record<string, number>;
  default_assumptions: Record<string, number>;
  default_reconciliation: Record<string, number>;
}
