"""Adjustment engine.

Standard sales-comparison direction, applied consistently:
  * comparable inferior to the subject  -> positive amount (comp adjusted UPWARD)
  * comparable superior to the subject  -> negative amount (comp adjusted DOWNWARD)

Every suggested adjustment records the subject value, the comparable value, the
unit math that produced the dollar amount, and a plain-language explanation.
Suggested amounts come from the per-CMA assumption set (sample values requiring
user review, never presented as market standards). Users can edit or delete
any adjustment; edits are re-flagged as manual and audit-logged by the API layer.
"""
from datetime import date
from typing import Any, Dict, List, Optional

from .similarity import condition_ordinal, months_between


def _fmt_money(amount: float) -> str:
    sign = "-" if amount < 0 else ""
    return "%s$%s" % (sign, format(round(abs(amount)), ","))


def suggest_adjustments(
    subject: Any, comp: Any, assumptions: Dict[str, float], as_of: Optional[date] = None
) -> List[Dict]:
    """Build the suggested adjustment list for one comparable.

    Categories with missing data on either side are skipped (never guessed).
    Returns dicts ready to persist as Adjustment rows (source="suggested").
    """
    as_of = as_of or date.today()
    out: List[Dict] = []

    # Time / market movement: comp sold in the past; in a rising market an
    # older sale understates today's value, so the comp adjusts upward.
    months = months_between(comp.sale_date, as_of)
    monthly_pct = assumptions.get("monthly_market_pct", 0.0)
    if months > 0 and monthly_pct != 0:
        amount = comp.sale_price * monthly_pct * months
        out.append({
            "category": "market_time",
            "subject_value": "valued as of %s" % as_of.isoformat(),
            "comparable_value": "sold %s" % comp.sale_date.isoformat(),
            "unit_description": "%.1f mo × %.2f%%/mo × %s"
            % (months, monthly_pct * 100, _fmt_money(comp.sale_price)),
            "amount": round(amount, 2),
            "explanation": "Assumed market movement of %.2f%% per month over %.1f months "
            "since the comparable sold. Sample assumption; review against local data."
            % (monthly_pct * 100, months),
        })

    # Living area
    s_sf, c_sf = subject.square_feet, comp.square_feet
    rate = assumptions.get("gla_per_sqft", 0.0)
    if s_sf and c_sf and s_sf > 0 and c_sf > 0 and rate != 0:
        diff = s_sf - c_sf
        if diff != 0:
            out.append({
                "category": "living_area",
                "subject_value": "%.0f sq ft" % s_sf,
                "comparable_value": "%.0f sq ft" % c_sf,
                "unit_description": "%.0f sq ft × %s/sq ft" % (diff, _fmt_money(rate)),
                "amount": round(diff * rate, 2),
                "explanation": "Comparable is %.0f sq ft %s than the subject."
                % (abs(diff), "smaller" if diff > 0 else "larger"),
            })

    # Lot size
    s_lot, c_lot = subject.lot_size, comp.lot_size
    lot_rate = assumptions.get("lot_per_sqft", 0.0)
    if s_lot and c_lot and s_lot > 0 and c_lot > 0 and lot_rate != 0:
        diff = s_lot - c_lot
        if diff != 0:
            out.append({
                "category": "lot_size",
                "subject_value": "%.0f sq ft lot" % s_lot,
                "comparable_value": "%.0f sq ft lot" % c_lot,
                "unit_description": "%.0f sq ft × %s/sq ft" % (diff, _fmt_money(lot_rate)),
                "amount": round(diff * lot_rate, 2),
                "explanation": "Comparable lot is %.0f sq ft %s than the subject's."
                % (abs(diff), "smaller" if diff > 0 else "larger"),
            })

    # Bedrooms
    per_bed = assumptions.get("per_bedroom", 0.0)
    if subject.bedrooms is not None and comp.bedrooms is not None and per_bed != 0:
        diff = subject.bedrooms - comp.bedrooms
        if diff != 0:
            out.append({
                "category": "bedrooms",
                "subject_value": str(subject.bedrooms),
                "comparable_value": str(comp.bedrooms),
                "unit_description": "%d bedroom(s) × %s" % (diff, _fmt_money(per_bed)),
                "amount": round(diff * per_bed, 2),
                "explanation": "Comparable has %d %s bedroom(s) than the subject."
                % (abs(diff), "fewer" if diff > 0 else "more"),
            })

    # Bathrooms
    per_bath = assumptions.get("per_bathroom", 0.0)
    if subject.bathrooms is not None and comp.bathrooms is not None and per_bath != 0:
        diff = subject.bathrooms - comp.bathrooms
        if diff != 0:
            out.append({
                "category": "bathrooms",
                "subject_value": str(subject.bathrooms),
                "comparable_value": str(comp.bathrooms),
                "unit_description": "%.1f bathroom(s) × %s" % (diff, _fmt_money(per_bath)),
                "amount": round(diff * per_bath, 2),
                "explanation": "Comparable has %.1f %s bathroom(s) than the subject."
                % (abs(diff), "fewer" if diff > 0 else "more"),
            })

    # Condition (ordinal steps on the poor..excellent scale)
    per_step = assumptions.get("per_condition_step", 0.0)
    s_cond = condition_ordinal(subject.condition)
    c_cond = condition_ordinal(comp.condition)
    if s_cond is not None and c_cond is not None and per_step != 0:
        diff = s_cond - c_cond
        if diff != 0:
            out.append({
                "category": "condition",
                "subject_value": subject.condition,
                "comparable_value": comp.condition,
                "unit_description": "%d step(s) × %s" % (diff, _fmt_money(per_step)),
                "amount": round(diff * per_step, 2),
                "explanation": "Comparable condition is %d step(s) %s on the "
                "poor→excellent scale." % (abs(diff), "below" if diff > 0 else "above"),
            })

    # Parking
    per_space = assumptions.get("per_parking_space", 0.0)
    if subject.parking_spaces is not None and comp.parking_spaces is not None and per_space != 0:
        diff = subject.parking_spaces - comp.parking_spaces
        if diff != 0:
            out.append({
                "category": "parking",
                "subject_value": "%d space(s)" % subject.parking_spaces,
                "comparable_value": "%d space(s)" % comp.parking_spaces,
                "unit_description": "%d space(s) × %s" % (diff, _fmt_money(per_space)),
                "amount": round(diff * per_space, 2),
                "explanation": "Comparable has %d %s parking space(s)."
                % (abs(diff), "fewer" if diff > 0 else "more"),
            })

    # Pool (flat amount). Unknown pool status on either side is skipped, never
    # treated as "no pool".
    pool_value = assumptions.get("pool_value", 0.0)
    if (pool_value != 0 and subject.has_pool is not None and comp.has_pool is not None
            and bool(subject.has_pool) != bool(comp.has_pool)):
        diff = (1 if subject.has_pool else 0) - (1 if comp.has_pool else 0)
        out.append({
            "category": "pool",
            "subject_value": "pool" if subject.has_pool else "no pool",
            "comparable_value": "pool" if comp.has_pool else "no pool",
            "unit_description": "flat %s" % _fmt_money(pool_value * diff),
            "amount": round(pool_value * diff, 2),
            "explanation": "Subject %s a pool; comparable %s."
            % ("has" if subject.has_pool else "lacks",
               "has one" if comp.has_pool else "does not"),
        })

    return out


def adjusted_price(sale_price: float, amounts: List[float]) -> float:
    """adjusted_sale_price = original_sale_price + sum(all_adjustments)"""
    return sale_price + sum(amounts)


def adjusted_ppsf(adj_price: float, square_feet: Optional[float]) -> Optional[float]:
    """Adjusted price per square foot; None when square footage is invalid."""
    if not square_feet or square_feet <= 0:
        return None
    return adj_price / square_feet


def adjustment_percentages(sale_price: float, amounts: List[float]) -> Dict[str, Optional[float]]:
    """Gross (sum of absolute) and net adjustment as fractions of sale price."""
    if not sale_price or sale_price <= 0:
        return {"gross_pct": None, "net_pct": None}
    return {
        "gross_pct": sum(abs(a) for a in amounts) / sale_price,
        "net_pct": sum(amounts) / sale_price,
    }
