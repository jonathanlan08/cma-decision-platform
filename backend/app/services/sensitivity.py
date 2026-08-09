"""Assumption sensitivity analysis.

Answers "which assumptions actually move the estimate?" by re-running the
suggested-adjustment + reconciliation pipeline with each assumption varied
±variation_pct (relative), one at a time.

Semantics, deliberately transparent:
  * Manual adjustments are held fixed — only assumption-driven suggested
    amounts are recomputed for each variation.
  * The baseline is recomputed the same way (manual + fresh suggestions from
    the current assumptions), so baseline and variations are always
    comparable. It may differ slightly from the stored valuation if the user
    edited assumptions without regenerating suggestions.
  * Nothing is persisted; this is a read-only what-if view.
"""
from datetime import date
from typing import Any, Dict, List, Optional

from .adjustments import adjusted_ppsf, adjusted_price, suggest_adjustments
from .reconciliation import reconcile

NOTE = (
    "Each assumption is varied one at a time; suggested adjustments are "
    "recomputed while manual adjustments stay fixed. Baseline uses the same "
    "reconstruction, so it may differ slightly from the stored valuation if "
    "suggestions were not regenerated after an assumption change."
)


def _central_for(
    subject: Any,
    included: List[Any],
    assumptions: Dict[str, float],
    reconciliation_params: Dict[str, float],
    as_of: Optional[date],
) -> Optional[float]:
    items = []
    for comp in included:
        manual = [a.amount for a in comp.adjustments if a.source == "manual"]
        suggested = [
            spec["amount"] for spec in suggest_adjustments(subject, comp, assumptions, as_of)
        ]
        adj_price = adjusted_price(comp.sale_price, manual + suggested)
        selection = comp.selection
        items.append({
            "comp_id": comp.id,
            "address": comp.address,
            "adjusted_price": adj_price,
            "ppsf": adjusted_ppsf(adj_price, comp.square_feet),
            "similarity": selection.similarity_score if selection else None,
            "multiplier": selection.user_weight_multiplier if selection else 1.0,
            "sale_date": comp.sale_date,
            "gross_pct": None,
        })
    result = reconcile(items, reconciliation_params, as_of=as_of)
    return result["central_estimate"]


def sensitivity_analysis(
    subject: Any,
    comparables: List[Any],
    assumptions: Dict[str, float],
    reconciliation_params: Dict[str, float],
    variation_pct: float = 0.20,
    as_of: Optional[date] = None,
) -> Dict:
    """Return {baseline_central, variation_pct, note, items} with items sorted
    by absolute impact, largest first. Zero-valued assumptions are skipped
    (a relative variation of zero is still zero)."""
    included = [
        comp for comp in comparables
        if comp.selection is None or comp.selection.included
    ]
    if not included:
        return {
            "baseline_central": None,
            "variation_pct": variation_pct,
            "note": NOTE,
            "items": [],
        }

    baseline = _central_for(subject, included, assumptions, reconciliation_params, as_of)
    items = []
    for key, value in assumptions.items():
        if value == 0:
            continue
        low_value = value * (1 - variation_pct)
        high_value = value * (1 + variation_pct)
        central_low = _central_for(
            subject, included, dict(assumptions, **{key: low_value}),
            reconciliation_params, as_of,
        )
        central_high = _central_for(
            subject, included, dict(assumptions, **{key: high_value}),
            reconciliation_params, as_of,
        )
        items.append({
            "assumption": key,
            "value": value,
            "low_value": round(low_value, 6),
            "high_value": round(high_value, 6),
            "central_low": central_low,
            "central_high": central_high,
            "delta_low": round(central_low - baseline, 2)
            if central_low is not None and baseline is not None else None,
            "delta_high": round(central_high - baseline, 2)
            if central_high is not None and baseline is not None else None,
        })

    items.sort(
        key=lambda item: max(
            abs(item["delta_low"] or 0), abs(item["delta_high"] or 0)
        ),
        reverse=True,
    )
    return {
        "baseline_central": baseline,
        "variation_pct": variation_pct,
        "note": NOTE,
        "items": items,
    }
