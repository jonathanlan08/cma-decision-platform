"""Adjustment management and valuation reconciliation."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..constants import CALC_VERSION
from ..database import get_db
from ..models import Adjustment, ValuationResult
from ..schemas import (
    AdjustmentIn,
    AdjustmentOut,
    AdjustmentUpdate,
    ComparableOut,
    SensitivityOut,
    ValuationOut,
)
from ..services.adjustments import (
    adjusted_ppsf,
    adjusted_price,
    adjustment_percentages,
    suggest_adjustments,
)
from ..services.audit import log_event
from ..services.fingerprint import suggestions_fingerprint, valuation_fingerprint
from ..services.reconciliation import reconcile
from ..services.sensitivity import sensitivity_analysis
from .helpers import (
    comparable_out,
    ensure_config,
    ensure_selection,
    get_cma_or_404,
    get_comparable_or_404,
    refresh_similarity,
    suggestions_outdated,
    touch,
    valuation_out,
)

router = APIRouter(prefix="/api", tags=["Adjustments & valuation"])


@router.post("/cmas/{cma_id}/adjustments/suggest", response_model=List[ComparableOut])
def suggest_all_adjustments(cma_id: int, db: Session = Depends(get_db)):
    """Regenerate suggested adjustments for every comparable from the current
    assumption set. Manual adjustments are preserved; previous suggested rows
    are replaced (that replacement is audit-logged)."""
    cma = get_cma_or_404(db, cma_id)
    if cma.subject is None:
        raise HTTPException(status_code=400,
                            detail="Enter the subject property before suggesting adjustments")
    config = ensure_config(db, cma)
    # Record the full input state that produced these suggestions: the
    # assumption set (for audit visibility) and a fingerprint of assumptions +
    # subject + comparable fields (the outdatedness authority).
    config.suggestions_assumptions = dict(config.assumptions)
    config.suggestions_fingerprint = suggestions_fingerprint(cma, config.assumptions)
    total = 0
    for comp in cma.comparables:
        removed = [a for a in comp.adjustments if a.source == "suggested"]
        for adj in removed:
            db.delete(adj)
        for spec in suggest_adjustments(cma.subject, comp, config.assumptions):
            db.add(Adjustment(comparable_id=comp.id, source="suggested", **spec))
            total += 1
    log_event(
        db, cma.id, "adjustments_suggested",
        "Generated %d suggested adjustment(s) across %d comparable(s) from the "
        "current assumption set. Manual adjustments were preserved."
        % (total, len(cma.comparables)),
        details={"assumptions": config.assumptions},
    )
    touch(cma)
    db.commit()
    db.expire_all()
    cma = get_cma_or_404(db, cma_id)
    return [comparable_out(comp, cma.subject) for comp in cma.comparables]


@router.post("/comparables/{comp_id}/adjustments", response_model=AdjustmentOut,
             status_code=201)
def add_manual_adjustment(comp_id: int, payload: AdjustmentIn, db: Session = Depends(get_db)):
    comp = get_comparable_or_404(db, comp_id)
    adj = Adjustment(comparable_id=comp.id, source="manual", **payload.model_dump())
    db.add(adj)
    db.flush()
    log_event(db, comp.cma_id, "adjustment_added",
              "Added manual %s adjustment of $%s to %s."
              % (adj.category, format(round(adj.amount), ","), comp.address),
              entity_type="adjustment", entity_id=adj.id,
              details={"category": adj.category, "amount": adj.amount,
                       "explanation": adj.explanation})
    touch(comp.cma)
    db.commit()
    db.refresh(adj)
    return AdjustmentOut.model_validate(adj)


@router.patch("/adjustments/{adjustment_id}", response_model=AdjustmentOut)
def update_adjustment(adjustment_id: int, payload: AdjustmentUpdate,
                      db: Session = Depends(get_db)):
    adj = db.get(Adjustment, adjustment_id)
    if adj is None:
        raise HTTPException(status_code=404, detail="Adjustment not found")
    changes = payload.model_dump(exclude_unset=True)
    old_amount = adj.amount
    amount_changed = "amount" in changes and changes["amount"] != adj.amount
    explanation_changed = ("explanation" in changes
                           and changes["explanation"] != adj.explanation)
    if amount_changed:
        adj.amount = changes["amount"]
        # An edited suggested adjustment becomes a manual override.
        adj.source = "manual"
    if "explanation" in changes:
        adj.explanation = changes["explanation"]
    # Only real changes reach the audit trail; a no-op PATCH must not create a
    # misleading "amount changed" event.
    if amount_changed:
        log_event(db, adj.comparable.cma_id, "adjustment_edited",
                  "Changed %s adjustment on %s from $%s to $%s (manual override)."
                  % (adj.category, adj.comparable.address,
                     format(round(old_amount), ","), format(round(adj.amount), ",")),
                  entity_type="adjustment", entity_id=adj.id,
                  details={"from": old_amount, "to": adj.amount,
                           "explanation": adj.explanation})
    elif explanation_changed:
        log_event(db, adj.comparable.cma_id, "adjustment_explanation_updated",
                  "Updated the explanation on the %s adjustment for %s."
                  % (adj.category, adj.comparable.address),
                  entity_type="adjustment", entity_id=adj.id,
                  details={"explanation": adj.explanation})
    if amount_changed or explanation_changed:
        touch(adj.comparable.cma)
    db.commit()
    db.refresh(adj)
    return AdjustmentOut.model_validate(adj)


@router.delete("/adjustments/{adjustment_id}", status_code=204)
def delete_adjustment(adjustment_id: int, db: Session = Depends(get_db)):
    adj = db.get(Adjustment, adjustment_id)
    if adj is None:
        raise HTTPException(status_code=404, detail="Adjustment not found")
    log_event(db, adj.comparable.cma_id, "adjustment_deleted",
              "Removed %s adjustment of $%s from %s."
              % (adj.category, format(round(adj.amount), ","), adj.comparable.address),
              entity_type="adjustment", entity_id=adj.id)
    cma = adj.comparable.cma
    db.delete(adj)
    touch(cma)
    db.commit()


@router.get("/cmas/{cma_id}/sensitivity", response_model=SensitivityOut)
def get_sensitivity(
    cma_id: int,
    variation_pct: float = Query(default=0.20, gt=0, le=1.0),
    db: Session = Depends(get_db),
):
    """Read-only what-if: vary each assumption ±variation_pct and report how
    the central estimate moves. Nothing is persisted or audit-logged."""
    cma = get_cma_or_404(db, cma_id)
    if cma.subject is None:
        raise HTTPException(status_code=400,
                            detail="Enter the subject property before running sensitivity")
    config = ensure_config(db, cma)
    result = sensitivity_analysis(
        cma.subject, cma.comparables, config.assumptions, config.reconciliation,
        variation_pct=variation_pct,
    )
    db.commit()  # ensure_config may have created the default config row
    return SensitivityOut(**result)


@router.get("/cmas/{cma_id}/valuation", response_model=ValuationOut)
def get_latest_valuation(cma_id: int, db: Session = Depends(get_db)):
    cma = get_cma_or_404(db, cma_id)
    if not cma.valuations:
        raise HTTPException(status_code=404, detail="No valuation has been calculated yet")
    return valuation_out(cma, cma.valuations[-1])


@router.post("/cmas/{cma_id}/valuation/recalculate", response_model=ValuationOut)
def recalculate_valuation(cma_id: int, db: Session = Depends(get_db)):
    """Refresh similarity scores, then reconcile all included comparables into
    a stored ValuationResult (kept as history for the audit trail)."""
    cma = get_cma_or_404(db, cma_id)
    config = ensure_config(db, cma)
    refresh_similarity(db, cma)

    items = []
    for comp in cma.comparables:
        selection = ensure_selection(db, comp)
        if not selection.included:
            continue
        amounts = [a.amount for a in comp.adjustments]
        adj_price = adjusted_price(comp.sale_price, amounts)
        pcts = adjustment_percentages(comp.sale_price, amounts)
        items.append({
            "comp_id": comp.id,
            "address": comp.address,
            "adjusted_price": adj_price,
            "ppsf": adjusted_ppsf(adj_price, comp.square_feet),
            "similarity": selection.similarity_score,
            "multiplier": selection.user_weight_multiplier,
            "sale_date": comp.sale_date,
            "gross_pct": pcts["gross_pct"],
        })

    result = reconcile(items, config.reconciliation)
    # Provenance check: suggested amounts are derived from assumptions, so a
    # valuation computed from suggestions of an OLDER assumption set is
    # internally inconsistent even though its own inputs are current.
    if suggestions_outdated(cma, config):
        result["warnings"].append({
            "code": "outdated_suggestions",
            "message": "The suggested adjustments were generated from an earlier "
            "assumption set. Regenerate suggested adjustments so this valuation "
            "reflects the current assumptions.",
        })
    valuation = ValuationResult(
        cma_id=cma.id,
        calc_version=CALC_VERSION,
        central_estimate=result["central_estimate"],
        low_estimate=result["low_estimate"],
        high_estimate=result["high_estimate"],
        median_adjusted=result["median_adjusted"],
        weighted_ppsf=result["weighted_ppsf"],
        dispersion=result["dispersion"],
        cov=result["cov"],
        included_count=result["included_count"],
        effective_count=result["effective_count"],
        input_fingerprint=valuation_fingerprint(cma, config),
        warnings=result["warnings"],
        per_comparable=result["per_comparable"],
    )
    db.add(valuation)
    db.flush()
    central = result["central_estimate"]
    log_event(
        db, cma.id, "valuation_recalculated",
        "Recalculated the valuation from %d included comparable(s): central "
        "estimate %s, range %s – %s. (%s)" % (
            result["included_count"],
            "$%s" % format(round(central), ",") if central else "n/a",
            "$%s" % format(round(result["low_estimate"]), ",")
            if result["low_estimate"] else "n/a",
            "$%s" % format(round(result["high_estimate"]), ",")
            if result["high_estimate"] else "n/a",
            CALC_VERSION,
        ),
        entity_type="valuation", entity_id=valuation.id,
        details={"warnings": result["warnings"],
                 "per_comparable": result["per_comparable"]},
    )
    touch(cma)
    db.commit()
    db.refresh(valuation)
    return valuation_out(cma, valuation)
