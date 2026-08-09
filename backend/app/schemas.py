"""Pydantic request/response schemas (v2). All API I/O is validated here;
calculation logic stays in app/services."""
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .constants import CMA_STATUSES, CONDITION_SCALE, PROPERTY_TYPES


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- CMA ---------------------------------------------------------------------

class CMACreate(BaseModel):
    title: str = Field(default="Untitled CMA", max_length=255)


class CMAUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    status: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("status")
    @classmethod
    def check_status(cls, v):
        if v is not None and v not in CMA_STATUSES:
            raise ValueError("status must be one of: %s" % ", ".join(CMA_STATUSES))
        return v


class ValuationOut(ORMModel):
    id: int
    calc_version: str
    created_at: datetime
    central_estimate: Optional[float]
    low_estimate: Optional[float]
    high_estimate: Optional[float]
    median_adjusted: Optional[float]
    weighted_ppsf: Optional[float]
    dispersion: Optional[float]
    cov: Optional[float]
    included_count: int
    warnings: Optional[List[Dict[str, Any]]]
    per_comparable: Optional[List[Dict[str, Any]]]


class SubjectIn(BaseModel):
    address: str = Field(min_length=1, max_length=255)
    city: Optional[str] = Field(default=None, max_length=100)
    zip_code: Optional[str] = Field(default=None, max_length=10)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    property_type: str = "single_family"
    bedrooms: Optional[int] = Field(default=None, ge=0, le=50)
    bathrooms: Optional[float] = Field(default=None, ge=0, le=50)
    square_feet: Optional[float] = Field(default=None, gt=0)
    lot_size: Optional[float] = Field(default=None, ge=0)
    year_built: Optional[int] = Field(default=None, ge=1800, le=2100)
    condition: Optional[str] = None
    parking_spaces: Optional[int] = Field(default=None, ge=0, le=50)
    has_pool: bool = False
    renovation_notes: Optional[str] = None
    agent_notes: Optional[str] = None

    @field_validator("property_type")
    @classmethod
    def check_type(cls, v):
        if v not in PROPERTY_TYPES:
            raise ValueError("property_type must be one of: %s" % ", ".join(PROPERTY_TYPES))
        return v

    @field_validator("condition")
    @classmethod
    def check_condition(cls, v):
        if v is not None and v not in CONDITION_SCALE:
            raise ValueError("condition must be one of: %s" % ", ".join(CONDITION_SCALE))
        return v


class SubjectOut(ORMModel):
    id: int
    address: str
    city: Optional[str]
    zip_code: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    property_type: str
    bedrooms: Optional[int]
    bathrooms: Optional[float]
    square_feet: Optional[float]
    lot_size: Optional[float]
    year_built: Optional[int]
    condition: Optional[str]
    parking_spaces: Optional[int]
    has_pool: bool
    renovation_notes: Optional[str]
    agent_notes: Optional[str]


class CMASummary(ORMModel):
    id: int
    title: str
    status: str
    created_at: datetime
    updated_at: datetime
    subject_address: Optional[str] = None
    comparable_count: int = 0
    included_count: int = 0
    strategy_count: int = 0
    report_count: int = 0
    latest_valuation: Optional[ValuationOut] = None


class CMADetail(CMASummary):
    notes: Optional[str] = None
    subject: Optional[SubjectOut] = None


# --- Comparables -------------------------------------------------------------

class ComparableIn(BaseModel):
    address: str = Field(min_length=1, max_length=255)
    city: Optional[str] = Field(default=None, max_length=100)
    zip_code: Optional[str] = Field(default=None, max_length=10)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    property_type: str = "single_family"
    sale_price: float = Field(gt=0)
    sale_date: date
    square_feet: float = Field(gt=0)
    lot_size: Optional[float] = Field(default=None, ge=0)
    bedrooms: int = Field(ge=0, le=50)
    bathrooms: float = Field(ge=0, le=50)
    year_built: Optional[int] = Field(default=None, ge=1800, le=2100)
    condition: Optional[str] = None
    parking_spaces: Optional[int] = Field(default=None, ge=0, le=50)
    has_pool: bool = False
    distance_from_subject: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = None
    source: Optional[str] = "manual-entry"

    @field_validator("property_type")
    @classmethod
    def check_type(cls, v):
        if v not in PROPERTY_TYPES:
            raise ValueError("property_type must be one of: %s" % ", ".join(PROPERTY_TYPES))
        return v

    @field_validator("condition")
    @classmethod
    def check_condition(cls, v):
        if v is not None and v not in CONDITION_SCALE:
            raise ValueError("condition must be one of: %s" % ", ".join(CONDITION_SCALE))
        return v

    @field_validator("sale_date")
    @classmethod
    def check_sale_date(cls, v):
        if v > date.today():
            raise ValueError("sale_date cannot be in the future")
        return v


class ComparableUpdate(BaseModel):
    """Partial update; same validation rules as ComparableIn."""
    address: Optional[str] = Field(default=None, min_length=1, max_length=255)
    city: Optional[str] = None
    zip_code: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    property_type: Optional[str] = None
    sale_price: Optional[float] = Field(default=None, gt=0)
    sale_date: Optional[date] = None
    square_feet: Optional[float] = Field(default=None, gt=0)
    lot_size: Optional[float] = Field(default=None, ge=0)
    bedrooms: Optional[int] = Field(default=None, ge=0, le=50)
    bathrooms: Optional[float] = Field(default=None, ge=0, le=50)
    year_built: Optional[int] = Field(default=None, ge=1800, le=2100)
    condition: Optional[str] = None
    parking_spaces: Optional[int] = Field(default=None, ge=0, le=50)
    has_pool: Optional[bool] = None
    distance_from_subject: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = None
    source: Optional[str] = None

    @field_validator("property_type")
    @classmethod
    def check_type(cls, v):
        if v is not None and v not in PROPERTY_TYPES:
            raise ValueError("property_type must be one of: %s" % ", ".join(PROPERTY_TYPES))
        return v

    @field_validator("condition")
    @classmethod
    def check_condition(cls, v):
        if v is not None and v not in CONDITION_SCALE:
            raise ValueError("condition must be one of: %s" % ", ".join(CONDITION_SCALE))
        return v


class AdjustmentOut(ORMModel):
    id: int
    category: str
    subject_value: Optional[str]
    comparable_value: Optional[str]
    unit_description: Optional[str]
    amount: float
    direction: str
    source: str
    explanation: Optional[str]
    updated_at: datetime


class SelectionOut(ORMModel):
    included: bool
    similarity_score: Optional[float]
    similarity_breakdown: Optional[Dict[str, Any]]
    user_weight_multiplier: float
    exclusion_reason: Optional[str]


class ComparableOut(ORMModel):
    id: int
    address: str
    city: Optional[str]
    zip_code: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    property_type: str
    sale_price: float
    sale_date: date
    square_feet: float
    lot_size: Optional[float]
    bedrooms: int
    bathrooms: float
    year_built: Optional[int]
    condition: Optional[str]
    parking_spaces: Optional[int]
    has_pool: bool
    distance_from_subject: Optional[float]
    notes: Optional[str]
    source: Optional[str]
    selection: Optional[SelectionOut] = None
    adjustments: List[AdjustmentOut] = []
    # Computed by the API layer:
    effective_distance_miles: Optional[float] = None
    adjusted_price: Optional[float] = None
    adjusted_ppsf: Optional[float] = None
    gross_adjustment_pct: Optional[float] = None
    net_adjustment_pct: Optional[float] = None


class SelectionUpdate(BaseModel):
    included: Optional[bool] = None
    user_weight_multiplier: Optional[float] = Field(default=None, ge=0, le=10)
    exclusion_reason: Optional[str] = None


class CSVImportResult(BaseModel):
    imported_count: int
    error_count: int
    comparables: List[ComparableOut]
    errors: List[Dict[str, Any]]


# --- Adjustments -------------------------------------------------------------

class AdjustmentIn(BaseModel):
    category: str = Field(min_length=1, max_length=50)
    amount: float
    subject_value: Optional[str] = Field(default=None, max_length=100)
    comparable_value: Optional[str] = Field(default=None, max_length=100)
    unit_description: Optional[str] = Field(default=None, max_length=255)
    explanation: Optional[str] = None


class AdjustmentUpdate(BaseModel):
    amount: Optional[float] = None
    explanation: Optional[str] = None


# --- Configuration -----------------------------------------------------------

class ConfigOut(ORMModel):
    weights: Dict[str, float]
    similarity_params: Dict[str, float]
    assumptions: Dict[str, float]
    reconciliation: Dict[str, float]
    updated_at: datetime


class ConfigUpdate(BaseModel):
    weights: Optional[Dict[str, float]] = None
    similarity_params: Optional[Dict[str, float]] = None
    assumptions: Optional[Dict[str, float]] = None
    reconciliation: Optional[Dict[str, float]] = None

    @field_validator("weights")
    @classmethod
    def check_weights(cls, v):
        if v is not None:
            for key, value in v.items():
                if value < 0:
                    raise ValueError("weight '%s' cannot be negative" % key)
            if sum(v.values()) <= 0:
                raise ValueError("at least one weight must be positive")
        return v


# --- Sensitivity -------------------------------------------------------------

class SensitivityItem(BaseModel):
    assumption: str
    value: float
    low_value: float
    high_value: float
    central_low: Optional[float]
    central_high: Optional[float]
    delta_low: Optional[float]
    delta_high: Optional[float]


class SensitivityOut(BaseModel):
    baseline_central: Optional[float]
    variation_pct: float
    note: str
    items: List[SensitivityItem]


# --- Strategies --------------------------------------------------------------

class StrategyOut(ORMModel):
    id: int
    key: str
    name: str
    list_price: float
    is_user_modified: bool
    derived: Dict[str, Any]
    updated_at: datetime


class StrategyUpdate(BaseModel):
    list_price: float = Field(gt=0)


# --- Audit / reports / meta --------------------------------------------------

class AuditEventOut(ORMModel):
    id: int
    timestamp: datetime
    actor: str
    event_type: str
    entity_type: Optional[str]
    entity_id: Optional[int]
    summary: str
    details: Optional[Dict[str, Any]]
    calc_version: str


class ReportOut(ORMModel):
    id: int
    created_at: datetime
    calc_version: str
    format: str


class MetaOut(BaseModel):
    calc_version: str
    disclaimer: str
    condition_scale: List[str]
    property_types: List[str]
    default_weights: Dict[str, float]
    default_similarity_params: Dict[str, float]
    default_assumptions: Dict[str, float]
    default_reconciliation: Dict[str, float]
