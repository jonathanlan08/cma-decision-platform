"""Similarity scoring: perfect matches, boundary cases, missing data, and
weight renormalization."""
import pytest

from app.constants import DEFAULT_SIMILARITY_PARAMS, DEFAULT_WEIGHTS
from app.services.similarity import compute_similarity, haversine_miles

from .conftest import AS_OF, make_comp, make_subject

WEIGHTS = DEFAULT_WEIGHTS
PARAMS = DEFAULT_SIMILARITY_PARAMS


def component(result, name):
    return next(c for c in result["components"] if c["name"] == name)


def test_identical_comparable_scores_100():
    result = compute_similarity(make_subject(), make_comp(), WEIGHTS, PARAMS, as_of=AS_OF)
    assert result["score"] == 100.0
    for comp in result["components"]:
        assert comp["score"] == 100.0
        assert not comp["missing"]


def test_contributions_sum_to_total_score():
    comp = make_comp(square_feet=1700, bedrooms=2, condition="average",
                     distance_from_subject=1.5)
    result = compute_similarity(make_subject(), comp, WEIGHTS, PARAMS, as_of=AS_OF)
    total = sum(c["contribution"] for c in result["components"])
    assert result["score"] == pytest.approx(total, abs=0.05)


def test_effective_weights_sum_to_one():
    result = compute_similarity(make_subject(), make_comp(), WEIGHTS, PARAMS, as_of=AS_OF)
    assert sum(c["effective_weight"] for c in result["components"]) == pytest.approx(1.0, abs=0.001)


def test_proximity_boundaries():
    subject = make_subject()
    at_max = compute_similarity(
        subject, make_comp(distance_from_subject=PARAMS["max_distance_miles"]),
        WEIGHTS, PARAMS, as_of=AS_OF)
    beyond = compute_similarity(
        subject, make_comp(distance_from_subject=PARAMS["max_distance_miles"] * 2),
        WEIGHTS, PARAMS, as_of=AS_OF)
    halfway = compute_similarity(
        subject, make_comp(distance_from_subject=PARAMS["max_distance_miles"] / 2),
        WEIGHTS, PARAMS, as_of=AS_OF)
    assert component(at_max, "proximity")["score"] == 0.0
    assert component(beyond, "proximity")["score"] == 0.0
    assert component(halfway, "proximity")["score"] == pytest.approx(50.0)


def test_haversine_known_distance():
    # ~0.1 degree of longitude at 34°N is roughly 5.7 miles.
    distance = haversine_miles(34.0, -118.0, 34.0, -118.1)
    assert 5.4 < distance < 6.0


def test_coordinates_preferred_over_stated_distance():
    subject = make_subject(latitude=34.0, longitude=-118.0)
    comp = make_comp(latitude=34.0, longitude=-118.0, distance_from_subject=2.9)
    result = compute_similarity(subject, comp, WEIGHTS, PARAMS, as_of=AS_OF)
    assert component(result, "proximity")["score"] == 100.0  # haversine 0, not 2.9 mi


def test_bedroom_cap_boundary():
    exact_cap = compute_similarity(
        make_subject(), make_comp(bedrooms=3 + PARAMS["bedroom_cap"]),
        WEIGHTS, PARAMS, as_of=AS_OF)
    one_off = compute_similarity(
        make_subject(), make_comp(bedrooms=4), WEIGHTS, PARAMS, as_of=AS_OF)
    assert component(exact_cap, "bedrooms")["score"] == 0.0
    assert component(one_off, "bedrooms")["score"] == pytest.approx(100 * (1 - 1 / 3), abs=0.01)


def test_property_type_mismatch_scores_zero():
    result = compute_similarity(
        make_subject(), make_comp(property_type="condo"), WEIGHTS, PARAMS, as_of=AS_OF)
    assert component(result, "property_type")["score"] == 0.0
    assert result["score"] < 100.0


def test_recency_decay():
    from datetime import date
    result = compute_similarity(
        make_subject(), make_comp(sale_date=date(2026, 2, 1)),  # ~6 months before AS_OF
        WEIGHTS, PARAMS, as_of=AS_OF)
    assert 45.0 < component(result, "recency")["score"] < 55.0


def test_missing_component_renormalizes_weights():
    """No location info at all: proximity drops out; remaining weights scale up."""
    comp = make_comp(distance_from_subject=None)
    result = compute_similarity(make_subject(), comp, WEIGHTS, PARAMS, as_of=AS_OF)
    assert "proximity" in result["missing_components"]
    prox = component(result, "proximity")
    assert prox["missing"] and prox["effective_weight"] == 0.0
    available = [c for c in result["components"] if not c["missing"]]
    assert sum(c["effective_weight"] for c in available) == pytest.approx(1.0, abs=0.001)
    assert result["score"] == 100.0  # everything else identical


def test_zero_square_feet_marks_component_missing():
    result = compute_similarity(
        make_subject(), make_comp(square_feet=0), WEIGHTS, PARAMS, as_of=AS_OF)
    assert "living_area" in result["missing_components"]


def test_missing_condition_marks_component_missing():
    result = compute_similarity(
        make_subject(condition=None), make_comp(), WEIGHTS, PARAMS, as_of=AS_OF)
    assert "condition" in result["missing_components"]


def test_all_weighted_components_missing_gives_none_score():
    subject = make_subject()
    comp = make_comp(distance_from_subject=None)
    result = compute_similarity(subject, comp, {"proximity": 1.0}, PARAMS, as_of=AS_OF)
    assert result["score"] is None


def test_custom_weights_change_score():
    comp = make_comp(property_type="condo")  # only mismatch
    all_on_type = compute_similarity(
        make_subject(), comp, {"property_type": 1.0}, PARAMS, as_of=AS_OF)
    ignoring_type = compute_similarity(
        make_subject(), comp, {"living_area": 1.0}, PARAMS, as_of=AS_OF)
    assert all_on_type["score"] == 0.0
    assert ignoring_type["score"] == 100.0


def test_score_bounded_0_to_100():
    comp = make_comp(square_feet=100, bedrooms=10, bathrooms=9, property_type="other",
                     condition="poor", year_built=1900, distance_from_subject=50,
                     lot_size=100000)
    result = compute_similarity(make_subject(), comp, WEIGHTS, PARAMS, as_of=AS_OF)
    assert 0.0 <= result["score"] <= 100.0
