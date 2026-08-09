"""Listing strategy scenarios."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ListingStrategy
from ..schemas import StrategyOut, StrategyUpdate
from ..services.audit import log_event
from ..services.strategies import derive_metrics, generate_default_strategies
from .helpers import get_cma_or_404, latest_valuation, touch

router = APIRouter(prefix="/api", tags=["Listing strategies"])


def _included_adjusted_values(valuation) -> List[float]:
    if valuation is None or not valuation.per_comparable:
        return []
    return [entry["adjusted_price"] for entry in valuation.per_comparable]


@router.get("/cmas/{cma_id}/strategies", response_model=List[StrategyOut])
def list_strategies(cma_id: int, db: Session = Depends(get_db)):
    cma = get_cma_or_404(db, cma_id)
    return [StrategyOut.model_validate(s) for s in cma.strategies]


@router.post("/cmas/{cma_id}/strategies/generate", response_model=List[StrategyOut])
def generate_strategies(cma_id: int, db: Session = Depends(get_db)):
    """Create/update the three standard scenarios from the latest valuation.
    User-modified prices are kept; their derived metrics are refreshed against
    the new central estimate."""
    cma = get_cma_or_404(db, cma_id)
    valuation = latest_valuation(cma)
    if valuation is None or not valuation.central_estimate:
        raise HTTPException(status_code=400,
                            detail="Calculate a valuation before generating strategies")
    central = valuation.central_estimate
    comp_values = _included_adjusted_values(valuation)
    existing = {s.key: s for s in cma.strategies}

    for spec in generate_default_strategies(central, comp_values):
        current = existing.get(spec["key"])
        if current is None:
            db.add(ListingStrategy(cma_id=cma.id, key=spec["key"], name=spec["name"],
                                   list_price=spec["list_price"], derived=spec["derived"]))
        elif current.is_user_modified:
            derived = derive_metrics(current.list_price, central, comp_values)
            derived["description"] = spec["derived"].get("description")
            current.derived = derived
        else:
            current.list_price = spec["list_price"]
            current.derived = spec["derived"]

    log_event(
        db, cma.id, "strategies_generated",
        "Generated listing strategy scenarios from the central estimate of $%s. "
        "User-modified prices were preserved." % format(round(central), ","),
        details={"central_estimate": central},
    )
    touch(cma)
    db.commit()
    db.refresh(cma)
    return [StrategyOut.model_validate(s) for s in cma.strategies]


@router.patch("/strategies/{strategy_id}", response_model=StrategyOut)
def update_strategy(strategy_id: int, payload: StrategyUpdate, db: Session = Depends(get_db)):
    strategy = db.get(ListingStrategy, strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    cma = strategy.cma
    valuation = latest_valuation(cma)
    if valuation is None or not valuation.central_estimate:
        raise HTTPException(status_code=400, detail="No valuation available")
    old_price = strategy.list_price
    strategy.list_price = payload.list_price
    strategy.is_user_modified = True
    description = strategy.derived.get("description") if strategy.derived else None
    derived = derive_metrics(payload.list_price, valuation.central_estimate,
                             _included_adjusted_values(valuation))
    derived["description"] = description
    strategy.derived = derived
    log_event(db, cma.id, "strategy_price_changed",
              "Changed %s strategy list price from $%s to $%s (user override)."
              % (strategy.name, format(round(old_price), ","),
                 format(round(payload.list_price), ",")),
              entity_type="listing_strategy", entity_id=strategy.id,
              details={"from": old_price, "to": payload.list_price})
    touch(cma)
    db.commit()
    db.refresh(strategy)
    return StrategyOut.model_validate(strategy)
