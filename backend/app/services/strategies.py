"""Listing strategy scenarios.

Deterministic, documented heuristics: scenario estimates, NOT validated
predictions of days-on-market or sale probability. Buyer interest and
price-reduction risk are qualitative levels derived from the list price's
percentage distance from the central estimate (thresholds in constants.py).
"""
from typing import Dict, List, Optional

from ..constants import (
    STRATEGY_DEFAULTS,
    STRATEGY_INTEREST_THRESHOLDS,
    STRATEGY_RISK_THRESHOLDS,
)

SCENARIO_CAVEAT = (
    "Scenario estimate from documented heuristics based on the list price's "
    "distance from the indicated value. Not an empirically validated prediction."
)


def interest_level(pct_diff: float) -> str:
    if pct_diff <= STRATEGY_INTEREST_THRESHOLDS["high_below"]:
        return "High"
    if pct_diff <= STRATEGY_INTEREST_THRESHOLDS["low_above"]:
        return "Moderate"
    return "Low"


def reduction_risk(pct_diff: float) -> str:
    if pct_diff <= STRATEGY_RISK_THRESHOLDS["low_below"]:
        return "Low"
    if pct_diff <= STRATEGY_RISK_THRESHOLDS["high_above"]:
        return "Moderate"
    return "High"


def _marketing_notes(pct_diff: float) -> str:
    if pct_diff <= -0.02:
        return ("Positioned to generate early traffic and potential multiple offers; "
                "prepare the seller for offer-review timing and negotiation above list.")
    if pct_diff <= 0.03:
        return ("Positioned at market; success depends on presentation, photography, "
                "and responsiveness during the first two weekends of exposure.")
    return ("Positioned above the indicated value; expect a smaller buyer pool, "
            "longer exposure, and plan a price-review checkpoint (e.g., after 21 days).")


def derive_metrics(
    list_price: float,
    central_estimate: float,
    comparable_adjusted_values: Optional[List[float]] = None,
) -> Dict:
    """All derived, display-ready metrics for one strategy row."""
    pct_diff = (list_price - central_estimate) / central_estimate if central_estimate else 0.0
    comps = comparable_adjusted_values or []
    position_percentile = None
    if comps:
        below = sum(1 for v in comps if v < list_price)
        position_percentile = round(below / len(comps) * 100, 1)
    return {
        "pct_vs_value": round(pct_diff, 4),
        "dollar_vs_value": round(list_price - central_estimate, 2),
        "position_percentile": position_percentile,
        "buyer_interest": interest_level(pct_diff),
        "price_reduction_risk": reduction_risk(pct_diff),
        "marketing_notes": _marketing_notes(pct_diff),
        "assumptions": SCENARIO_CAVEAT,
    }


def generate_default_strategies(
    central_estimate: float, comparable_adjusted_values: Optional[List[float]] = None
) -> List[Dict]:
    """The three standard scenarios priced off the central estimate."""
    out = []
    for spec in STRATEGY_DEFAULTS:
        list_price = round(central_estimate * spec["pct_of_value"], -3)  # nearest $1,000
        derived = derive_metrics(list_price, central_estimate, comparable_adjusted_values)
        derived["description"] = spec["description"]
        out.append({
            "key": spec["key"],
            "name": spec["name"],
            "list_price": list_price,
            "derived": derived,
        })
    return out
