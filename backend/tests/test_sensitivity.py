"""Assumption sensitivity: direction, fixed manual adjustments, edge cases."""
from types import SimpleNamespace

import pytest

from app.constants import DEFAULT_ASSUMPTIONS, DEFAULT_RECONCILIATION
from app.services.sensitivity import sensitivity_analysis

from .conftest import AS_OF, make_comp, make_subject


def orm_like(comp, included=True, similarity=90.0, multiplier=1.0, manual_amounts=()):
    """Wrap a plain comp namespace with the selection/adjustments shape the
    service reads from ORM rows."""
    comp.id = getattr(comp, "id", 1)
    comp.selection = SimpleNamespace(
        included=included, similarity_score=similarity, user_weight_multiplier=multiplier,
    )
    comp.adjustments = [
        SimpleNamespace(amount=a, source="manual") for a in manual_amounts
    ]
    return comp


def run(subject, comps, assumptions=None, pct=0.20):
    return sensitivity_analysis(
        subject, comps, assumptions or dict(DEFAULT_ASSUMPTIONS),
        DEFAULT_RECONCILIATION, variation_pct=pct, as_of=AS_OF,
    )


def item_for(result, key):
    matches = [i for i in result["items"] if i["assumption"] == key]
    return matches[0] if matches else None


def test_no_included_comparables():
    comp = orm_like(make_comp(), included=False)
    result = run(make_subject(), [comp])
    assert result["baseline_central"] is None
    assert result["items"] == []


def test_zero_valued_assumptions_are_skipped():
    assumptions = dict.fromkeys(DEFAULT_ASSUMPTIONS, 0.0)
    comp = orm_like(make_comp(square_feet=1700))
    result = run(make_subject(), [comp], assumptions)
    assert result["items"] == []
    assert result["baseline_central"] == comp.sale_price  # no adjustments at all


def test_gla_sensitivity_direction():
    """Comp smaller than subject -> suggested GLA adjustment is positive ->
    raising $/sq ft raises the central estimate."""
    comp = orm_like(make_comp(square_feet=1700))  # subject 2000
    result = run(make_subject(), [comp])
    gla = item_for(result, "gla_per_sqft")
    assert gla is not None
    assert gla["delta_high"] > 0 > gla["delta_low"]
    # ±20% of a 300 sq ft × $150 adjustment = ±$9,000
    assert gla["delta_high"] == pytest.approx(9000, abs=1)
    assert gla["delta_low"] == pytest.approx(-9000, abs=1)


def test_irrelevant_assumption_has_zero_impact():
    """No pool difference -> pool assumption variation moves nothing."""
    comp = orm_like(make_comp(square_feet=1700))
    result = run(make_subject(), [comp])
    pool = item_for(result, "pool_value")
    assert pool is not None
    assert pool["delta_low"] == 0 and pool["delta_high"] == 0


def test_manual_adjustments_held_fixed():
    """A manual adjustment shifts the baseline but never varies."""
    plain = orm_like(make_comp(), manual_amounts=[-50_000])
    assumptions = dict.fromkeys(DEFAULT_ASSUMPTIONS, 0.0)
    result = run(make_subject(), [plain], assumptions)
    assert result["baseline_central"] == pytest.approx(plain.sale_price - 50_000)


def test_items_sorted_by_absolute_impact():
    comp = orm_like(make_comp(square_feet=1400, bedrooms=2))  # big GLA + bedroom diff
    result = run(make_subject(), [comp])
    impacts = [
        max(abs(i["delta_low"] or 0), abs(i["delta_high"] or 0)) for i in result["items"]
    ]
    assert impacts == sorted(impacts, reverse=True)
    assert result["items"][0]["assumption"] == "gla_per_sqft"


def test_variation_pct_scales_linearly():
    comp = orm_like(make_comp(square_feet=1700))
    narrow = item_for(run(make_subject(), [comp], pct=0.10), "gla_per_sqft")
    wide = item_for(run(make_subject(), [comp], pct=0.20), "gla_per_sqft")
    assert wide["delta_high"] == pytest.approx(narrow["delta_high"] * 2, abs=1)


def test_api_endpoint(client):
    from pathlib import Path
    sample = Path(__file__).resolve().parents[2] / "data" / "sample" / "comparables_sample.csv"
    cma_id = client.post("/api/cmas", json={"title": "Sensitivity"}).json()["id"]
    client.put("/api/cmas/%d/subject" % cma_id, json={
        "address": "12345 Demo Lane", "square_feet": 1850, "bedrooms": 3,
        "bathrooms": 2, "lot_size": 7200, "year_built": 1958, "condition": "good",
        "parking_spaces": 2,
    })
    with open(sample, "rb") as f:
        client.post("/api/cmas/%d/comparables/import-csv" % cma_id,
                    files={"file": ("s.csv", f, "text/csv")})
    client.post("/api/cmas/%d/similarity/recalculate" % cma_id)

    response = client.get("/api/cmas/%d/sensitivity" % cma_id)
    assert response.status_code == 200
    body = response.json()
    assert body["baseline_central"] is not None
    assert body["variation_pct"] == 0.20
    assert len(body["items"]) > 0
    assert "manual adjustments stay fixed" in body["note"]

    # No subject -> 400; invalid pct -> 422
    empty_id = client.post("/api/cmas", json={"title": "Empty"}).json()["id"]
    assert client.get("/api/cmas/%d/sensitivity" % empty_id).status_code == 400
    assert client.get("/api/cmas/%d/sensitivity?variation_pct=0" % cma_id).status_code == 422
