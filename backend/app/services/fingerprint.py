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


def _value(obj: Any, field: str):
    value = getattr(obj, field, None)
    if isinstance(value, date):
        return value.isoformat()
    return value


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
        "weights": dict(config.weights) if config else None,
        "similarity_params": dict(config.similarity_params) if config else None,
        "assumptions": dict(config.assumptions) if config else None,
        "reconciliation": dict(config.reconciliation) if config else None,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
