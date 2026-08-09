"""Adjustment engine: direction convention, unit math, missing data, totals."""
from datetime import date, timedelta

import pytest

from app.constants import DEFAULT_ASSUMPTIONS
from app.services.adjustments import (
    adjusted_ppsf,
    adjusted_price,
    adjustment_percentages,
    suggest_adjustments,
)
from app.services.similarity import months_between

from .conftest import AS_OF, make_comp, make_subject

A = DEFAULT_ASSUMPTIONS


def by_category(adjustments, category):
    matches = [a for a in adjustments if a["category"] == category]
    return matches[0] if matches else None


def test_identical_comp_same_day_needs_no_adjustments():
    result = suggest_adjustments(make_subject(), make_comp(), A, as_of=AS_OF)
    assert result == []


def test_inferior_comp_adjusts_upward():
    """Comp is 300 sq ft smaller (inferior) -> positive (upward) adjustment."""
    comp = make_comp(square_feet=1700)
    adj = by_category(suggest_adjustments(make_subject(), comp, A, as_of=AS_OF), "living_area")
    assert adj["amount"] == pytest.approx(300 * A["gla_per_sqft"])
    assert adj["amount"] > 0


def test_superior_comp_adjusts_downward():
    comp = make_comp(square_feet=2400)
    adj = by_category(suggest_adjustments(make_subject(), comp, A, as_of=AS_OF), "living_area")
    assert adj["amount"] == pytest.approx(-400 * A["gla_per_sqft"])
    assert adj["amount"] < 0


def test_bedroom_and_bathroom_directions():
    comp = make_comp(bedrooms=2, bathrooms=3.0)  # fewer beds (inferior), more baths (superior)
    result = suggest_adjustments(make_subject(), comp, A, as_of=AS_OF)
    assert by_category(result, "bedrooms")["amount"] == pytest.approx(A["per_bedroom"])
    assert by_category(result, "bathrooms")["amount"] == pytest.approx(-A["per_bathroom"])


def test_condition_steps():
    """Subject 'good' (4) vs comp 'fair' (2): comp 2 steps inferior -> +2 steps."""
    comp = make_comp(condition="fair")
    adj = by_category(suggest_adjustments(make_subject(), comp, A, as_of=AS_OF), "condition")
    assert adj["amount"] == pytest.approx(2 * A["per_condition_step"])


def test_pool_both_directions_and_parity():
    subject_with_pool = make_subject(has_pool=True)
    comp_no_pool = make_comp(has_pool=False)
    up = by_category(suggest_adjustments(subject_with_pool, comp_no_pool, A, as_of=AS_OF), "pool")
    assert up["amount"] == pytest.approx(A["pool_value"])

    down = by_category(
        suggest_adjustments(make_subject(), make_comp(has_pool=True), A, as_of=AS_OF), "pool")
    assert down["amount"] == pytest.approx(-A["pool_value"])

    both = suggest_adjustments(subject_with_pool, make_comp(has_pool=True), A, as_of=AS_OF)
    assert by_category(both, "pool") is None


def test_market_time_adjustment_positive_in_rising_market():
    sale_date = AS_OF - timedelta(days=304)  # ~10 months
    comp = make_comp(sale_date=sale_date)
    adj = by_category(suggest_adjustments(make_subject(), comp, A, as_of=AS_OF), "market_time")
    expected = comp.sale_price * A["monthly_market_pct"] * months_between(sale_date, AS_OF)
    assert adj["amount"] == pytest.approx(expected, abs=0.01)
    assert adj["amount"] > 0


def test_missing_lot_size_skips_lot_adjustment():
    comp = make_comp(lot_size=None, square_feet=1800)
    result = suggest_adjustments(make_subject(), comp, A, as_of=AS_OF)
    assert by_category(result, "lot_size") is None
    assert by_category(result, "living_area") is not None  # others still produced


def test_missing_condition_skips_condition_adjustment():
    result = suggest_adjustments(
        make_subject(), make_comp(condition=None, square_feet=1800), A, as_of=AS_OF)
    assert by_category(result, "condition") is None


def test_every_suggested_adjustment_is_fully_documented():
    comp = make_comp(square_feet=1700, bedrooms=2, condition="fair", has_pool=True,
                     sale_date=date(2026, 2, 1))
    for adj in suggest_adjustments(make_subject(), comp, A, as_of=AS_OF):
        assert adj["category"]
        assert adj["subject_value"]
        assert adj["comparable_value"]
        assert adj["unit_description"]
        assert adj["explanation"]


def test_adjusted_price_is_sale_plus_sum():
    assert adjusted_price(1_000_000, [50_000, -20_000]) == 1_030_000
    assert adjusted_price(1_000_000, []) == 1_000_000


def test_adjusted_ppsf_and_invalid_sqft():
    assert adjusted_ppsf(1_030_000, 2000) == pytest.approx(515.0)
    assert adjusted_ppsf(1_030_000, 0) is None
    assert adjusted_ppsf(1_030_000, None) is None


def test_adjustment_percentages():
    pcts = adjustment_percentages(1_000_000, [50_000, -20_000])
    assert pcts["gross_pct"] == pytest.approx(0.07)
    assert pcts["net_pct"] == pytest.approx(0.03)
    assert adjustment_percentages(0, [50_000]) == {"gross_pct": None, "net_pct": None}


def test_zero_assumption_disables_category():
    assumptions = dict(A, gla_per_sqft=0.0)
    result = suggest_adjustments(
        make_subject(), make_comp(square_feet=1700), assumptions, as_of=AS_OF)
    assert by_category(result, "living_area") is None
