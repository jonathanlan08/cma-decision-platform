"""Shared router utilities: lookups, config access, and response builders."""
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..constants import (
    DEFAULT_ASSUMPTIONS,
    DEFAULT_RECONCILIATION,
    DEFAULT_SIMILARITY_PARAMS,
    DEFAULT_WEIGHTS,
)
from ..models import (
    CMAAnalysis,
    ComparableProperty,
    ComparableSelection,
    WeightConfiguration,
)
from ..schemas import ComparableOut, ValuationOut
from ..services.adjustments import adjusted_ppsf, adjusted_price, adjustment_percentages
from ..services.fingerprint import suggestions_fingerprint, valuation_fingerprint
from ..services.similarity import compute_similarity, resolve_distance_miles


def get_cma_or_404(db: Session, cma_id: int) -> CMAAnalysis:
    cma = db.get(CMAAnalysis, cma_id)
    if cma is None:
        raise HTTPException(status_code=404, detail="CMA analysis %d not found" % cma_id)
    return cma


def get_comparable_or_404(db: Session, comp_id: int) -> ComparableProperty:
    comp = db.get(ComparableProperty, comp_id)
    if comp is None:
        raise HTTPException(status_code=404, detail="Comparable %d not found" % comp_id)
    return comp


def ensure_config(db: Session, cma: CMAAnalysis) -> WeightConfiguration:
    if cma.weight_config is None:
        cma.weight_config = WeightConfiguration(
            weights=dict(DEFAULT_WEIGHTS),
            similarity_params=dict(DEFAULT_SIMILARITY_PARAMS),
            assumptions=dict(DEFAULT_ASSUMPTIONS),
            reconciliation=dict(DEFAULT_RECONCILIATION),
        )
        db.add(cma.weight_config)
    return cma.weight_config


def ensure_selection(db: Session, comp: ComparableProperty) -> ComparableSelection:
    if comp.selection is None:
        comp.selection = ComparableSelection(included=True, user_weight_multiplier=1.0)
        db.add(comp.selection)
    return comp.selection


def refresh_similarity(db: Session, cma: CMAAnalysis) -> int:
    """Recompute similarity for every comparable in the CMA. Requires a subject.
    Returns the number of comparables scored."""
    if cma.subject is None:
        raise HTTPException(status_code=400, detail="Enter the subject property before "
                            "calculating similarity scores")
    config = ensure_config(db, cma)
    count = 0
    for comp in cma.comparables:
        selection = ensure_selection(db, comp)
        result = compute_similarity(
            cma.subject, comp, config.weights, config.similarity_params
        )
        selection.similarity_score = result["score"]
        selection.similarity_breakdown = result
        count += 1
    return count


def comparable_out(comp: ComparableProperty, subject=None) -> ComparableOut:
    """Response model with derived pricing fields computed from stored rows."""
    out = ComparableOut.model_validate(comp)
    amounts = [a.amount for a in comp.adjustments]
    adj_price = adjusted_price(comp.sale_price, amounts)
    pcts = adjustment_percentages(comp.sale_price, amounts)
    out.adjusted_price = round(adj_price, 2)
    out.adjusted_ppsf = (
        round(adjusted_ppsf(adj_price, comp.square_feet), 2)
        if adjusted_ppsf(adj_price, comp.square_feet) is not None else None
    )
    out.gross_adjustment_pct = (
        round(pcts["gross_pct"], 4) if pcts["gross_pct"] is not None else None
    )
    out.net_adjustment_pct = (
        round(pcts["net_pct"], 4) if pcts["net_pct"] is not None else None
    )
    if subject is not None:
        distance = resolve_distance_miles(subject, comp)
        out.effective_distance_miles = round(distance, 2) if distance is not None else None
    else:
        out.effective_distance_miles = comp.distance_from_subject
    return out


def touch(cma: CMAAnalysis) -> None:
    """Force updated_at to refresh even when only child rows changed."""
    from ..models import utcnow
    cma.updated_at = utcnow()


def latest_valuation(cma: CMAAnalysis):
    return cma.valuations[-1] if cma.valuations else None


def valuation_staleness(cma: CMAAnalysis, valuation) -> Optional[bool]:
    """True when the CMA's inputs no longer match what the valuation was
    computed from; None when unknown (no stored fingerprint)."""
    if valuation is None or valuation.input_fingerprint is None:
        return None
    return valuation.input_fingerprint != valuation_fingerprint(cma, cma.weight_config)


def suggestions_outdated(cma: CMAAnalysis, config) -> Optional[bool]:
    """True when stored suggested adjustments no longer follow from the data
    on screen. Suggested amounts are DERIVED from the assumption set AND the
    subject/comparable fields, so a change to any of those (a resized subject,
    an edited sale price, a newly added comparable) breaks the derivation
    chain even if the valuation's own fingerprint is current. None when
    unknown (no snapshot recorded)."""
    has_suggested = any(
        adj.source == "suggested"
        for comp in cma.comparables for adj in comp.adjustments
    )
    if not has_suggested:
        return False
    if config is None or config.suggestions_fingerprint is None:
        return None
    return config.suggestions_fingerprint != suggestions_fingerprint(
        cma, config.assumptions)


def valuation_out(cma: CMAAnalysis, valuation) -> ValuationOut:
    """ValuationOut with the staleness flag stamped by the API layer."""
    out = ValuationOut.model_validate(valuation)
    out.stale = valuation_staleness(cma, valuation)
    return out


def money(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return "$%s" % format(round(value), ",")
