"""Transparent similarity scoring.

Each component maps a subject/comparable attribute pair onto a 0-100 score with
a documented linear curve. The overall score is the weighted average of the
available components, with weights renormalized when a component cannot be
computed (missing data) so the score stays on a 0-100 scale. The full breakdown
— per-component raw values, scores, effective weights, and contributions — is
returned and stored so no number is ever a black box.

All curves and weights come from the per-CMA WeightConfiguration; defaults live
in app/constants.py and are demonstration values, not appraisal standards.
"""
import math
from datetime import date
from typing import Any, Dict, List, Optional

from ..constants import CONDITION_SCALE

DAYS_PER_MONTH = 30.44


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in miles."""
    r_miles = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r_miles * math.asin(math.sqrt(a))


def condition_ordinal(condition: Optional[str]) -> Optional[int]:
    """Map the condition scale to 1..5 (poor..excellent). None if unknown."""
    if condition is None:
        return None
    try:
        return CONDITION_SCALE.index(condition.strip().lower()) + 1
    except ValueError:
        return None


def months_between(earlier: date, later: date) -> float:
    return max(0.0, (later - earlier).days / DAYS_PER_MONTH)


def _linear_score(diff: float, cap: float) -> float:
    """100 at diff=0 falling linearly to 0 at diff>=cap."""
    if cap <= 0:
        return 0.0
    return max(0.0, 1.0 - abs(diff) / cap) * 100.0


def resolve_distance_miles(subject: Any, comp: Any) -> Optional[float]:
    """Prefer haversine from coordinates; fall back to the CSV-provided
    distance_from_subject; None when neither is available."""
    if (
        getattr(subject, "latitude", None) is not None
        and getattr(subject, "longitude", None) is not None
        and getattr(comp, "latitude", None) is not None
        and getattr(comp, "longitude", None) is not None
    ):
        return haversine_miles(subject.latitude, subject.longitude, comp.latitude, comp.longitude)
    return getattr(comp, "distance_from_subject", None)


def _component_proximity(subject: Any, comp: Any, params: Dict) -> Dict:
    distance = resolve_distance_miles(subject, comp)
    max_d = params["max_distance_miles"]
    if distance is None:
        return {"missing": True, "detail": "No coordinates or distance provided"}
    score = _linear_score(distance, max_d)
    return {
        "missing": False,
        "score": score,
        "subject_value": "subject location",
        "comparable_value": "%.2f mi away" % distance,
        "detail": "%.2f mi of %.1f mi max (linear falloff)" % (distance, max_d),
    }


def _component_living_area(subject: Any, comp: Any, params: Dict) -> Dict:
    s, c = getattr(subject, "square_feet", None), getattr(comp, "square_feet", None)
    if not s or not c or s <= 0 or c <= 0:
        return {"missing": True, "detail": "Living area missing or invalid"}
    tolerance = params["living_area_tolerance"] * s
    score = _linear_score(c - s, tolerance)
    return {
        "missing": False,
        "score": score,
        "subject_value": "%.0f sq ft" % s,
        "comparable_value": "%.0f sq ft" % c,
        "detail": "Δ %.0f sq ft of ±%.0f sq ft tolerance" % (abs(c - s), tolerance),
    }


def _component_count(subject_val, comp_val, cap, unit: str) -> Dict:
    if subject_val is None or comp_val is None:
        return {"missing": True, "detail": "%s missing" % unit.capitalize()}
    score = _linear_score(comp_val - subject_val, cap)
    return {
        "missing": False,
        "score": score,
        "subject_value": str(subject_val),
        "comparable_value": str(comp_val),
        "detail": "Δ %.1f of %d %s cap" % (abs(comp_val - subject_val), cap, unit),
    }


def _component_property_type(subject: Any, comp: Any, params: Dict) -> Dict:
    s, c = getattr(subject, "property_type", None), getattr(comp, "property_type", None)
    if not s or not c:
        return {"missing": True, "detail": "Property type missing"}
    score = 100.0 if s == c else 0.0
    return {
        "missing": False,
        "score": score,
        "subject_value": s,
        "comparable_value": c,
        "detail": "Exact match" if score == 100.0 else "Type mismatch",
    }


def _component_lot_size(subject: Any, comp: Any, params: Dict) -> Dict:
    s, c = getattr(subject, "lot_size", None), getattr(comp, "lot_size", None)
    if not s or not c or s <= 0 or c <= 0:
        return {"missing": True, "detail": "Lot size missing or invalid"}
    tolerance = params["lot_size_tolerance"] * s
    score = _linear_score(c - s, tolerance)
    return {
        "missing": False,
        "score": score,
        "subject_value": "%.0f sq ft" % s,
        "comparable_value": "%.0f sq ft" % c,
        "detail": "Δ %.0f sq ft of ±%.0f sq ft tolerance" % (abs(c - s), tolerance),
    }


def _component_age(subject: Any, comp: Any, params: Dict) -> Dict:
    s, c = getattr(subject, "year_built", None), getattr(comp, "year_built", None)
    if s is None or c is None:
        return {"missing": True, "detail": "Year built missing"}
    score = _linear_score(c - s, params["age_cap_years"])
    return {
        "missing": False,
        "score": score,
        "subject_value": str(s),
        "comparable_value": str(c),
        "detail": "Δ %d yr of %d yr cap" % (abs(c - s), params["age_cap_years"]),
    }


def _component_recency(subject: Any, comp: Any, params: Dict, as_of: date) -> Dict:
    sale_date = getattr(comp, "sale_date", None)
    if sale_date is None:
        return {"missing": True, "detail": "Sale date missing"}
    months = months_between(sale_date, as_of)
    score = _linear_score(months, params["recency_cap_months"])
    return {
        "missing": False,
        "score": score,
        "subject_value": "as of %s" % as_of.isoformat(),
        "comparable_value": "sold %s" % sale_date.isoformat(),
        "detail": "%.1f mo ago of %d mo cap" % (months, params["recency_cap_months"]),
    }


def _component_condition(subject: Any, comp: Any, params: Dict) -> Dict:
    s = condition_ordinal(getattr(subject, "condition", None))
    c = condition_ordinal(getattr(comp, "condition", None))
    if s is None or c is None:
        return {"missing": True, "detail": "Condition missing or unrecognized"}
    score = _linear_score(c - s, params["condition_cap_steps"])
    return {
        "missing": False,
        "score": score,
        "subject_value": getattr(subject, "condition"),
        "comparable_value": getattr(comp, "condition"),
        "detail": "Δ %d step(s) of %d cap" % (abs(c - s), params["condition_cap_steps"]),
    }


def compute_similarity(
    subject: Any,
    comp: Any,
    weights: Dict[str, float],
    params: Dict[str, float],
    as_of: Optional[date] = None,
) -> Dict:
    """Return {"score": 0-100 | None, "components": [...], "missing_components": [...]}.

    Missing components are excluded and the remaining weights renormalized;
    each component entry records its configured weight, effective (renormalized)
    weight, score, and contribution (effective_weight × score).
    """
    as_of = as_of or date.today()
    raw: Dict[str, Dict] = {
        "proximity": _component_proximity(subject, comp, params),
        "living_area": _component_living_area(subject, comp, params),
        "bedrooms": _component_count(
            getattr(subject, "bedrooms", None), getattr(comp, "bedrooms", None),
            params["bedroom_cap"], "bedroom",
        ),
        "bathrooms": _component_count(
            getattr(subject, "bathrooms", None), getattr(comp, "bathrooms", None),
            params["bathroom_cap"], "bathroom",
        ),
        "property_type": _component_property_type(subject, comp, params),
        "lot_size": _component_lot_size(subject, comp, params),
        "age": _component_age(subject, comp, params),
        "recency": _component_recency(subject, comp, params, as_of),
        "condition": _component_condition(subject, comp, params),
    }

    available = {
        name: info for name, info in raw.items()
        if not info["missing"] and weights.get(name, 0) > 0
    }
    missing = [name for name, info in raw.items() if info["missing"]]
    total_weight = sum(weights[name] for name in available)

    components: List[Dict] = []
    score: Optional[float] = None
    if total_weight > 0:
        score = 0.0
        for name, info in raw.items():
            configured = weights.get(name, 0.0)
            entry = {
                "name": name,
                "weight": configured,
                "missing": info["missing"],
                "detail": info.get("detail"),
                "subject_value": info.get("subject_value"),
                "comparable_value": info.get("comparable_value"),
            }
            if name in available:
                effective = configured / total_weight
                contribution = effective * info["score"]
                entry.update({
                    "score": round(info["score"], 2),
                    "effective_weight": round(effective, 4),
                    "contribution": round(contribution, 2),
                })
                score += contribution
            else:
                entry.update({"score": None, "effective_weight": 0.0, "contribution": 0.0})
            components.append(entry)
        score = round(score, 2)
    else:
        components = [
            {"name": name, "weight": weights.get(name, 0.0), "missing": True,
             "score": None, "effective_weight": 0.0, "contribution": 0.0,
             "detail": info.get("detail")}
            for name, info in raw.items()
        ]

    return {
        "score": score,
        "as_of": as_of.isoformat(),
        "components": components,
        "missing_components": missing,
    }
