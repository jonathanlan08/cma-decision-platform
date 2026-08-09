"""Valuation input fingerprinting for staleness detection.

A ValuationResult stores the SHA-256 of every input that fed it: the subject's
pricing-relevant fields, each comparable's fields, its inclusion state, weight
multiplier and adjustments, the full per-CMA configuration, and the calculation
version. When the current fingerprint no longer matches the stored one, the
valuation (and anything derived from it) is stale, and the API says so instead
of presenting old numbers as current.

Only fields that can change a calculated number participate. Titles, notes, and
addresses are excluded on purpose so cosmetic edits do not flag staleness.
"""
import hashlib
import json
from datetime import date
from typing import Any, Optional

from ..constants import CALC_VERSION

# Fields of the subject that influence similarity or suggested adjustments.
SUBJECT_FIELDS = [
    "property_type", "bedrooms", "bathrooms", "square_feet", "lot_size",
    "year_built", "condition", "parking_spaces", "has_pool",
    "latitude", "longitude",
]

# Comparable fields that influence similarity, adjustments, or reconciliation.
COMPARABLE_FIELDS = SUBJECT_FIELDS + [
    "sale_price", "sale_date", "distance_from_subject",
]

# The inputs that shape SUGGESTED adjustment amounts specifically: the fields
# suggest_adjustments() actually reads. Deliberately excludes the as-of date
# (its daily drift would flag every analysis as outdated every morning).
SUGGESTION_SUBJECT_FIELDS = [
    "square_feet", "lot_size", "bedrooms", "bathrooms",
    "condition", "parking_spaces", "has_pool",
]
SUGGESTION_COMPARABLE_FIELDS = SUGGESTION_SUBJECT_FIELDS + ["sale_price", "sale_date"]


def _normalize(value: Any):
    """Make fingerprint leaves type-stable. SQLite/JSON round-trips can turn
    1850 into 1850.0 (and back); without normalization the same VALUE hashes
    differently before and after persistence, producing false staleness."""
    if isinstance(value, bool):  # bool is an int subclass; keep it a bool
        return value
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


def _normalize_dict(d: Any):
    return {k: _normalize(v) for k, v in d.items()} if d is not None else None


def _value(obj: Any, field: str):
    return _normalize(getattr(obj, field, None))


def valuation_fingerprint(cma: Any, config: Optional[Any]) -> str:
    """Deterministic SHA-256 over every valuation input of one CMA."""
    comparables = []
    for comp in sorted(cma.comparables, key=lambda c: c.id):
        selection = comp.selection
        comparables.append({
            "id": comp.id,
            "fields": {f: _value(comp, f) for f in COMPARABLE_FIELDS},
            "included": selection.included if selection else True,
            "multiplier": selection.user_weight_multiplier if selection else 1.0,
            "adjustments": [
                {"category": a.category, "amount": a.amount, "source": a.source}
                for a in sorted(comp.adjustments, key=lambda a: a.id)
            ],
        })
    payload = {
        "calc_version": CALC_VERSION,
        "subject": (
            {f: _value(cma.subject, f) for f in SUBJECT_FIELDS}
            if cma.subject is not None else None
        ),
        "comparables": comparables,
        "weights": _normalize_dict(config.weights) if config else None,
        "similarity_params": _normalize_dict(config.similarity_params) if config else None,
        "assumptions": _normalize_dict(config.assumptions) if config else None,
        "reconciliation": _normalize_dict(config.reconciliation) if config else None,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def suggestions_fingerprint(cma: Any, assumptions: Any) -> str:
    """SHA-256 over every input that shapes suggested adjustment amounts:
    the assumption set, the subject's priced fields, and each comparable's
    priced fields. Stored when suggestions are generated; a mismatch later
    means the stored suggested amounts no longer follow from the data on
    screen (e.g. the subject's square footage changed)."""
    payload = {
        "assumptions": _normalize_dict(assumptions),
        "subject": (
            {f: _value(cma.subject, f) for f in SUGGESTION_SUBJECT_FIELDS}
            if cma.subject is not None else None
        ),
        "comparables": [
            {"id": comp.id,
             **{f: _value(comp, f) for f in SUGGESTION_COMPARABLE_FIELDS}}
            for comp in sorted(cma.comparables, key=lambda c: c.id)
        ],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
