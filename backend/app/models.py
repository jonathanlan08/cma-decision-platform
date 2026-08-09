"""ORM entities.

Normalized around one CMAAnalysis owning a SubjectProperty, ComparableProperties
(each with a ComparableSelection and Adjustments), a WeightConfiguration,
ValuationResults, ListingStrategies, AuditEvents, and GeneratedReports.
"""
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    display_name: Mapped[str] = mapped_column(String(255), default="Demo Agent")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    analyses: Mapped[List["CMAAnalysis"]] = relationship(back_populates="user")


class CMAAnalysis(Base):
    __tablename__ = "cma_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(255), default="Untitled CMA")
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft|completed|archived
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship(back_populates="analyses")
    subject: Mapped[Optional["SubjectProperty"]] = relationship(
        back_populates="cma", uselist=False, cascade="all, delete-orphan"
    )
    comparables: Mapped[List["ComparableProperty"]] = relationship(
        back_populates="cma", cascade="all, delete-orphan"
    )
    weight_config: Mapped[Optional["WeightConfiguration"]] = relationship(
        back_populates="cma", uselist=False, cascade="all, delete-orphan"
    )
    valuations: Mapped[List["ValuationResult"]] = relationship(
        back_populates="cma", cascade="all, delete-orphan", order_by="ValuationResult.id"
    )
    strategies: Mapped[List["ListingStrategy"]] = relationship(
        back_populates="cma", cascade="all, delete-orphan"
    )
    audit_events: Mapped[List["AuditEvent"]] = relationship(
        back_populates="cma", cascade="all, delete-orphan", order_by="AuditEvent.id"
    )
    reports: Mapped[List["GeneratedReport"]] = relationship(
        back_populates="cma", cascade="all, delete-orphan"
    )


class SubjectProperty(Base):
    __tablename__ = "subject_properties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cma_id: Mapped[int] = mapped_column(ForeignKey("cma_analyses.id"), unique=True)
    address: Mapped[str] = mapped_column(String(255))
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    zip_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    property_type: Mapped[str] = mapped_column(String(30), default="single_family")
    bedrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    square_feet: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lot_size: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    year_built: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    condition: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    parking_spaces: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    has_pool: Mapped[bool] = mapped_column(Boolean, default=False)
    renovation_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    agent_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    cma: Mapped["CMAAnalysis"] = relationship(back_populates="subject")


class ComparableProperty(Base):
    __tablename__ = "comparable_properties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cma_id: Mapped[int] = mapped_column(ForeignKey("cma_analyses.id"))
    address: Mapped[str] = mapped_column(String(255))
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    zip_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # property_type and has_pool are nullable: an unknown value stays unknown
    # (skipped in scoring/adjustments) instead of being silently guessed.
    property_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    sale_price: Mapped[float] = mapped_column(Float)
    sale_date: Mapped[date] = mapped_column(Date)
    square_feet: Mapped[float] = mapped_column(Float)
    lot_size: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bedrooms: Mapped[int] = mapped_column(Integer)
    bathrooms: Mapped[float] = mapped_column(Float)
    year_built: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    condition: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    parking_spaces: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    has_pool: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    distance_from_subject: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # miles
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    cma: Mapped["CMAAnalysis"] = relationship(back_populates="comparables")
    selection: Mapped[Optional["ComparableSelection"]] = relationship(
        back_populates="comparable", uselist=False, cascade="all, delete-orphan"
    )
    adjustments: Mapped[List["Adjustment"]] = relationship(
        back_populates="comparable", cascade="all, delete-orphan", order_by="Adjustment.id"
    )


class ComparableSelection(Base):
    """Inclusion state, similarity score/breakdown, and per-comp weight override."""

    __tablename__ = "comparable_selections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    comparable_id: Mapped[int] = mapped_column(ForeignKey("comparable_properties.id"), unique=True)
    included: Mapped[bool] = mapped_column(Boolean, default=True)
    similarity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100
    similarity_breakdown: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    user_weight_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    exclusion_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    comparable: Mapped["ComparableProperty"] = relationship(back_populates="selection")


class Adjustment(Base):
    __tablename__ = "adjustments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    comparable_id: Mapped[int] = mapped_column(ForeignKey("comparable_properties.id"))
    category: Mapped[str] = mapped_column(String(50))  # market_time|living_area|lot_size|...
    subject_value: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    comparable_value: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    unit_description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    amount: Mapped[float] = mapped_column(Float)  # signed dollars; + adjusts comp upward
    source: Mapped[str] = mapped_column(String(20), default="suggested")  # suggested|manual
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    comparable: Mapped["ComparableProperty"] = relationship(back_populates="adjustments")

    @property
    def direction(self) -> str:
        if self.amount > 0:
            return "upward"
        if self.amount < 0:
            return "downward"
        return "none"


class WeightConfiguration(Base):
    """Per-CMA similarity weights, similarity curve parameters, adjustment
    assumptions, and reconciliation parameters. All user-editable."""

    __tablename__ = "weight_configurations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cma_id: Mapped[int] = mapped_column(ForeignKey("cma_analyses.id"), unique=True)
    weights: Mapped[dict] = mapped_column(JSON)
    similarity_params: Mapped[dict] = mapped_column(JSON)
    assumptions: Mapped[dict] = mapped_column(JSON)
    reconciliation: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    cma: Mapped["CMAAnalysis"] = relationship(back_populates="weight_config")


class ValuationResult(Base):
    __tablename__ = "valuation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cma_id: Mapped[int] = mapped_column(ForeignKey("cma_analyses.id"))
    calc_version: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    central_estimate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    low_estimate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    high_estimate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    median_adjusted: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weighted_ppsf: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dispersion: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # weighted std dev
    cov: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    included_count: Mapped[int] = mapped_column(Integer, default=0)
    # Number of included comparables that actually carry positive weight.
    effective_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # SHA-256 of the inputs this valuation was computed from; a mismatch with
    # the current inputs means the valuation is stale.
    input_fingerprint: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    warnings: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    per_comparable: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # weight snapshot

    cma: Mapped["CMAAnalysis"] = relationship(back_populates="valuations")


class ListingStrategy(Base):
    __tablename__ = "listing_strategies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cma_id: Mapped[int] = mapped_column(ForeignKey("cma_analyses.id"))
    key: Mapped[str] = mapped_column(String(30))  # market_entry|competitive|aspirational
    name: Mapped[str] = mapped_column(String(50))
    list_price: Mapped[float] = mapped_column(Float)
    is_user_modified: Mapped[bool] = mapped_column(Boolean, default=False)
    derived: Mapped[dict] = mapped_column(JSON)  # pct_vs_value, position, interest, risk, notes
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    cma: Mapped["CMAAnalysis"] = relationship(back_populates="strategies")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cma_id: Mapped[int] = mapped_column(ForeignKey("cma_analyses.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    actor: Mapped[str] = mapped_column(String(100), default="demo")
    event_type: Mapped[str] = mapped_column(String(60))
    entity_type: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    summary: Mapped[str] = mapped_column(Text)  # plain-language sentence for the audit screen
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    calc_version: Mapped[str] = mapped_column(String(20))

    cma: Mapped["CMAAnalysis"] = relationship(back_populates="audit_events")


class GeneratedReport(Base):
    __tablename__ = "generated_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cma_id: Mapped[int] = mapped_column(ForeignKey("cma_analyses.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    calc_version: Mapped[str] = mapped_column(String(20))
    format: Mapped[str] = mapped_column(String(10), default="html")  # html|pdf
    content_html: Mapped[str] = mapped_column(Text)
    pdf_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    cma: Mapped["CMAAnalysis"] = relationship(back_populates="reports")
