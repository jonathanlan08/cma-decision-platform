"""Valuation reconciliation.

Weights included comparables by similarity × user override multiplier, then:

  normalized_weight_i = raw_weight_i / sum(all_raw_weights)
  central_estimate    = sum(adjusted_value_i × normalized_weight_i)

The range is central ± k × weighted standard deviation (k configurable). This is
an analytical estimate, not a statistical confidence interval, and is labeled as
such everywhere it appears. Every warning condition is explicit and documented.
"""
import math
from datetime import date
from typing import Dict, List, Optional

from .similarity import months_between


def reconcile(items: List[Dict], params: Dict, as_of: Optional[date] = None) -> Dict:
    """items: one dict per INCLUDED comparable with keys:
        comp_id, address, adjusted_price, ppsf (optional), similarity (0-100 or None),
        multiplier (user weight override, >=0), sale_date (date), gross_pct (optional)

    Returns the full reconciliation result with per-comparable normalized weights.
    """
    as_of = as_of or date.today()
    warnings: List[Dict] = []

    if not items:
        return {
            "central_estimate": None, "low_estimate": None, "high_estimate": None,
            "median_adjusted": None, "weighted_ppsf": None, "dispersion": None,
            "cov": None, "included_count": 0, "effective_count": 0,
            "per_comparable": [],
            "warnings": [{
                "code": "no_comparables",
                "message": "No comparables are included, so a valuation cannot be calculated.",
            }],
        }

    n = len(items)

    # Raw weight = similarity (0-1) × user multiplier. Similarity already
    # contains the recency component, so recency is not double-counted here.
    # An unscored comparable (similarity None) gets ZERO weight, never a
    # default: it must not outrank scored comparables.
    raw_weights = []
    scored_flags = []
    for item in items:
        similarity = item.get("similarity")
        if similarity is None:
            raw_weights.append(0.0)
            scored_flags.append(False)
            warnings.append({
                "code": "unscored_comparable", "comp_id": item["comp_id"],
                "message": "%s has no similarity score and was given zero weight. "
                "Recalculate similarity scores for it to influence the estimate."
                % (item.get("address") or "A comparable"),
            })
        else:
            raw_weights.append(max(0.0, (similarity / 100.0) * item.get("multiplier", 1.0)))
            scored_flags.append(True)

    total = sum(raw_weights)
    if total <= 0:
        if not any(scored_flags):
            warnings.append({
                "code": "no_scored_comparables",
                "message": "No included comparable has a similarity score, so a "
                "weighted valuation cannot be calculated. Recalculate similarity "
                "scores first.",
            })
            per_comp = [{
                "comp_id": item["comp_id"], "address": item.get("address"),
                "adjusted_price": round(item["adjusted_price"], 2),
                "similarity": None, "multiplier": item.get("multiplier", 1.0),
                "raw_weight": 0.0, "normalized_weight": 0.0, "influence_pct": 0.0,
            } for item in items]
            return {
                "central_estimate": None, "low_estimate": None, "high_estimate": None,
                "median_adjusted": None, "weighted_ppsf": None, "dispersion": None,
                "cov": None, "included_count": n, "effective_count": 0,
                "per_comparable": per_comp, "warnings": warnings,
            }
        # Scores/multipliers zeroed everything out: fall back to equal weights
        # across the SCORED comparables only.
        warnings.append({
            "code": "zero_weights",
            "message": "All comparable weights were zero; equal weights were "
            "applied across the scored comparables.",
        })
        raw_weights = [1.0 if flag else 0.0 for flag in scored_flags]
        total = sum(raw_weights)
    norm_weights = [w / total for w in raw_weights]

    # Adequacy is judged on comparables that actually carry weight, not on the
    # raw included count: three included rows with weights [1, 0, 0] are one
    # effective comparable.
    effective_count = sum(1 for w in raw_weights if w > 0)
    if effective_count < 3:
        warnings.append({
            "code": "insufficient_comparables",
            "message": "Only %d comparable(s) carry weight in the reconciliation. "
            "At least 3 are recommended for a meaningful analysis." % effective_count,
        })

    values = [item["adjusted_price"] for item in items]
    central = sum(w * v for w, v in zip(norm_weights, values))

    # Weighted dispersion
    dispersion: Optional[float] = None
    cov: Optional[float] = None
    if n > 1:
        variance = sum(w * (v - central) ** 2 for w, v in zip(norm_weights, values))
        dispersion = math.sqrt(variance)
        cov = dispersion / central if central > 0 else None

    k = params.get("range_k", 1.0)
    if effective_count == 1:
        # One weighted comparable gives a zero-width dispersion; a nominal band
        # is more honest than false precision.
        pct = params.get("single_comp_range_pct", 0.05)
        low, high = central * (1 - pct), central * (1 + pct)
        warnings.append({
            "code": "single_comparable",
            "message": "Only one comparable carries weight; the range is a nominal "
            "±%.0f%% band, not a data-driven estimate." % (pct * 100),
        })
    else:
        low, high = central - k * dispersion, central + k * dispersion

    sorted_vals = sorted(values)
    mid = n // 2
    median = sorted_vals[mid] if n % 2 == 1 else (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0

    # Weighted price/sq ft over comps that have a valid ppsf, renormalized.
    ppsf_pairs = [
        (w, item["ppsf"]) for w, item in zip(norm_weights, items) if item.get("ppsf")
    ]
    weighted_ppsf = None
    if ppsf_pairs:
        ppsf_total = sum(w for w, _ in ppsf_pairs)
        if ppsf_total > 0:
            weighted_ppsf = sum(w * p for w, p in ppsf_pairs) / ppsf_total

    if cov is not None and cov > params.get("high_dispersion_cov", 0.15):
        warnings.append({
            "code": "high_dispersion",
            "message": "Adjusted values vary widely (coefficient of variation %.0f%%). "
            "The range should be treated with extra caution." % (cov * 100),
        })

    stale_months = params.get("stale_sale_months", 12)
    gross_warn = params.get("gross_adjustment_warn_pct", 0.25)
    outlier_pct = params.get("outlier_deviation_pct", 0.20)
    per_comp = []
    for item, raw_w, norm_w in zip(items, raw_weights, norm_weights):
        entry = {
            "comp_id": item["comp_id"],
            "address": item.get("address"),
            "adjusted_price": round(item["adjusted_price"], 2),
            "similarity": item.get("similarity"),
            "multiplier": item.get("multiplier", 1.0),
            "raw_weight": round(raw_w, 4),
            "normalized_weight": round(norm_w, 4),
            "influence_pct": round(norm_w * 100, 1),
        }
        per_comp.append(entry)

        sale_date = item.get("sale_date")
        if sale_date is not None and months_between(sale_date, as_of) > stale_months:
            warnings.append({
                "code": "stale_sale", "comp_id": item["comp_id"],
                "message": "%s sold more than %d months ago; the time adjustment "
                "carries more uncertainty." % (item.get("address", "A comparable"), stale_months),
            })
        gross = item.get("gross_pct")
        if gross is not None and gross > gross_warn:
            warnings.append({
                "code": "large_gross_adjustment", "comp_id": item["comp_id"],
                "message": "%s required gross adjustments of %.0f%% of its sale price, "
                "which weakens its reliability as a comparable."
                % (item.get("address", "A comparable"), gross * 100),
            })
        if median > 0 and abs(item["adjusted_price"] - median) / median > outlier_pct:
            warnings.append({
                "code": "outlier", "comp_id": item["comp_id"],
                "message": "%s's adjusted value deviates more than %.0f%% from the "
                "median and may be an outlier." % (item.get("address", "A comparable"),
                                                   outlier_pct * 100),
            })

    return {
        "central_estimate": round(central, 2),
        "low_estimate": round(low, 2),
        "high_estimate": round(high, 2),
        "median_adjusted": round(median, 2),
        "weighted_ppsf": round(weighted_ppsf, 2) if weighted_ppsf is not None else None,
        "dispersion": round(dispersion, 2) if dispersion is not None else None,
        "cov": round(cov, 4) if cov is not None else None,
        "included_count": n,
        "effective_count": effective_count,
        "per_comparable": per_comp,
        "warnings": warnings,
    }
