"""Valuation reconciliation: weighting, dispersion, ranges, and warnings."""
from datetime import date, timedelta

import pytest

from app.constants import DEFAULT_RECONCILIATION
from app.services.reconciliation import reconcile

from .conftest import AS_OF

P = DEFAULT_RECONCILIATION


def item(comp_id=1, value=1_000_000.0, similarity=90.0, multiplier=1.0,
         sale_date=None, ppsf=None, gross_pct=0.05, address=None):
    return {
        "comp_id": comp_id,
        "address": address or ("Comp %d" % comp_id),
        "adjusted_price": value,
        "ppsf": ppsf,
        "similarity": similarity,
        "multiplier": multiplier,
        "sale_date": sale_date or AS_OF - timedelta(days=30),
        "gross_pct": gross_pct,
    }


def warning_codes(result):
    return {w["code"] for w in result["warnings"]}


def test_no_comparables():
    result = reconcile([], P, as_of=AS_OF)
    assert result["central_estimate"] is None
    assert result["included_count"] == 0
    assert warning_codes(result) == {"no_comparables"}


def test_single_comparable_uses_nominal_band():
    result = reconcile([item(value=1_000_000)], P, as_of=AS_OF)
    assert result["central_estimate"] == 1_000_000
    assert result["low_estimate"] == pytest.approx(950_000)
    assert result["high_estimate"] == pytest.approx(1_050_000)
    assert result["dispersion"] is None
    assert {"single_comparable", "insufficient_comparables"} <= warning_codes(result)


def test_fewer_than_three_warns():
    result = reconcile([item(1, 1_000_000), item(2, 1_010_000)], P, as_of=AS_OF)
    assert "insufficient_comparables" in warning_codes(result)


def test_equal_weights_give_mean_and_normalized_weights():
    result = reconcile([item(1, 900_000), item(2, 1_100_000)], P, as_of=AS_OF)
    assert result["central_estimate"] == pytest.approx(1_000_000)
    weights = [e["normalized_weight"] for e in result["per_comparable"]]
    assert sum(weights) == pytest.approx(1.0, abs=0.001)
    assert weights[0] == pytest.approx(0.5, abs=0.001)


def test_similarity_weighting():
    """Similarity 90 vs 45 -> 2:1 influence."""
    result = reconcile(
        [item(1, 1_200_000, similarity=90), item(2, 900_000, similarity=45)],
        P, as_of=AS_OF)
    expected = (2 * 1_200_000 + 900_000) / 3
    assert result["central_estimate"] == pytest.approx(expected, abs=1)
    assert result["per_comparable"][0]["influence_pct"] == pytest.approx(66.7, abs=0.1)


def test_manual_weight_override_shifts_influence():
    base = reconcile([item(1, 1_200_000), item(2, 900_000)], P, as_of=AS_OF)
    boosted = reconcile(
        [item(1, 1_200_000, multiplier=2.0), item(2, 900_000)], P, as_of=AS_OF)
    assert boosted["central_estimate"] > base["central_estimate"]
    assert boosted["per_comparable"][0]["influence_pct"] == pytest.approx(66.7, abs=0.1)


def test_zero_multiplier_removes_influence():
    result = reconcile(
        [item(1, 5_000_000, multiplier=0.0), item(2, 1_000_000)], P, as_of=AS_OF)
    assert result["central_estimate"] == pytest.approx(1_000_000)


def test_all_zero_weights_fall_back_to_equal():
    result = reconcile(
        [item(1, 900_000, multiplier=0.0), item(2, 1_100_000, multiplier=0.0)],
        P, as_of=AS_OF)
    assert result["central_estimate"] == pytest.approx(1_000_000)
    assert "zero_weights" in warning_codes(result)


def test_weighted_dispersion_and_range():
    result = reconcile([item(1, 900_000), item(2, 1_100_000)], P, as_of=AS_OF)
    assert result["dispersion"] == pytest.approx(100_000, abs=1)
    assert result["low_estimate"] == pytest.approx(900_000, abs=1)
    assert result["high_estimate"] == pytest.approx(1_100_000, abs=1)
    assert result["cov"] == pytest.approx(0.1, abs=0.001)


def test_range_k_parameter():
    params = dict(P, range_k=2.0)
    result = reconcile([item(1, 900_000), item(2, 1_100_000)], params, as_of=AS_OF)
    assert result["low_estimate"] == pytest.approx(800_000, abs=1)
    assert result["high_estimate"] == pytest.approx(1_200_000, abs=1)


def test_median_odd_and_even():
    odd = reconcile([item(1, 900_000), item(2, 1_000_000), item(3, 2_000_000)],
                    P, as_of=AS_OF)
    assert odd["median_adjusted"] == 1_000_000
    even = reconcile([item(1, 900_000), item(2, 1_100_000)], P, as_of=AS_OF)
    assert even["median_adjusted"] == pytest.approx(1_000_000)


def test_extreme_outlier_flagged():
    result = reconcile(
        [item(1, 1_000_000), item(2, 1_020_000), item(3, 2_500_000)], P, as_of=AS_OF)
    outliers = [w for w in result["warnings"] if w["code"] == "outlier"]
    assert len(outliers) == 1
    assert outliers[0]["comp_id"] == 3


def test_high_dispersion_warns():
    result = reconcile([item(1, 700_000), item(2, 1_300_000)], P, as_of=AS_OF)
    assert "high_dispersion" in warning_codes(result)


def test_stale_sale_warns():
    stale = item(1, 1_000_000, sale_date=AS_OF - timedelta(days=430))
    result = reconcile([stale, item(2, 1_000_000), item(3, 1_000_000)], P, as_of=AS_OF)
    stale_warnings = [w for w in result["warnings"] if w["code"] == "stale_sale"]
    assert len(stale_warnings) == 1 and stale_warnings[0]["comp_id"] == 1


def test_large_gross_adjustment_warns():
    heavy = item(1, 1_000_000, gross_pct=0.30)
    result = reconcile([heavy, item(2, 1_000_000, gross_pct=0.05)], P, as_of=AS_OF)
    codes = [w for w in result["warnings"] if w["code"] == "large_gross_adjustment"]
    assert len(codes) == 1 and codes[0]["comp_id"] == 1


def test_weighted_ppsf_skips_missing():
    result = reconcile(
        [item(1, 1_000_000, ppsf=500.0), item(2, 1_000_000, ppsf=None)], P, as_of=AS_OF)
    assert result["weighted_ppsf"] == pytest.approx(500.0)


def test_weighted_ppsf_none_when_no_sqft_anywhere():
    result = reconcile([item(1, 1_000_000, ppsf=None)], P, as_of=AS_OF)
    assert result["weighted_ppsf"] is None


def test_unscored_comparable_gets_zero_weight_not_full_weight():
    """calc-v1.1: similarity=None must never outrank scored comparables."""
    result = reconcile(
        [item(1, 900_000, similarity=None), item(2, 1_100_000, similarity=100.0)],
        P, as_of=AS_OF)
    # All the weight goes to the scored comparable.
    assert result["central_estimate"] == pytest.approx(1_100_000)
    by_id = {e["comp_id"]: e for e in result["per_comparable"]}
    assert by_id[1]["influence_pct"] == 0.0
    assert by_id[2]["influence_pct"] == 100.0
    codes = [w["code"] for w in result["warnings"]]
    assert "unscored_comparable" in codes
    assert result["effective_count"] == 1


def test_all_unscored_comparables_produce_no_estimate():
    result = reconcile(
        [item(1, 900_000, similarity=None), item(2, 1_100_000, similarity=None)],
        P, as_of=AS_OF)
    assert result["central_estimate"] is None
    assert result["effective_count"] == 0
    codes = [w["code"] for w in result["warnings"]]
    assert "no_scored_comparables" in codes


def test_zero_weight_rows_do_not_inflate_adequacy():
    """Three included rows with effective weights [1, 0, 0] are ONE effective
    comparable: warn as insufficient and use the nominal single-comp band."""
    result = reconcile(
        [
            item(1, 1_000_000, similarity=90.0, multiplier=1.0),
            item(2, 900_000, similarity=90.0, multiplier=0.0),
            item(3, 1_200_000, similarity=90.0, multiplier=0.0),
        ],
        P, as_of=AS_OF)
    assert result["included_count"] == 3
    assert result["effective_count"] == 1
    codes = [w["code"] for w in result["warnings"]]
    assert "insufficient_comparables" in codes
    assert "single_comparable" in codes
    # Nominal band, not a zero-width range.
    assert result["low_estimate"] < result["central_estimate"] < result["high_estimate"]


def test_sale_date_none_is_tolerated():
    entry = item(1, 1_000_000)
    entry["sale_date"] = None
    result = reconcile([entry, item(2, 1_000_000)], P, as_of=AS_OF)
    assert result["central_estimate"] == pytest.approx(1_000_000)


def test_as_of_defaults_to_today():
    result = reconcile([item(1, 1_000_000, sale_date=date.today())], P)
    assert result["central_estimate"] == 1_000_000
