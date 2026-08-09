"""Listing strategy heuristics: default scenarios, threshold labels, position."""
import pytest

from app.services.strategies import (
    derive_metrics,
    generate_default_strategies,
    interest_level,
    reduction_risk,
)


def test_three_default_strategies():
    strategies = generate_default_strategies(1_000_000)
    assert [s["key"] for s in strategies] == ["market_entry", "competitive", "aspirational"]
    prices = {s["key"]: s["list_price"] for s in strategies}
    assert prices["market_entry"] == 970_000
    assert prices["competitive"] == 1_000_000
    assert prices["aspirational"] == 1_050_000


def test_prices_rounded_to_thousand():
    for s in generate_default_strategies(1_234_567):
        assert s["list_price"] % 1000 == 0


def test_interest_thresholds():
    assert interest_level(-0.05) == "High"
    assert interest_level(-0.02) == "High"      # boundary inclusive
    assert interest_level(-0.019) == "Moderate"
    assert interest_level(0.03) == "Moderate"   # boundary inclusive
    assert interest_level(0.031) == "Low"


def test_risk_thresholds():
    assert reduction_risk(-0.03) == "Low"
    assert reduction_risk(0.0) == "Low"         # boundary inclusive
    assert reduction_risk(0.01) == "Moderate"
    assert reduction_risk(0.05) == "Moderate"   # boundary inclusive
    assert reduction_risk(0.051) == "High"


def test_derived_metrics_content():
    derived = derive_metrics(1_050_000, 1_000_000, [900_000, 1_000_000, 1_100_000])
    assert derived["pct_vs_value"] == pytest.approx(0.05)
    assert derived["dollar_vs_value"] == 50_000
    assert derived["position_percentile"] == pytest.approx(66.7, abs=0.1)
    assert derived["buyer_interest"] == "Low"
    assert derived["price_reduction_risk"] == "Moderate"
    assert "heuristic" in derived["assumptions"].lower()
    assert derived["marketing_notes"]


def test_position_percentile_without_comps():
    derived = derive_metrics(1_000_000, 1_000_000, [])
    assert derived["position_percentile"] is None


def test_zero_central_estimate_guard():
    derived = derive_metrics(500_000, 0.0, [])
    assert derived["pct_vs_value"] == 0.0
