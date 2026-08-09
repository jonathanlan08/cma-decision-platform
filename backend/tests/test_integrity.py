"""Regression tests for the 2026-08 integrity hardening (calc-v1.1).

Covers the audit findings: staleness detection and the report consistency
gate, strict configuration validation, CSV non-finite/surplus-cell handling,
unknown-stays-unknown semantics for pool/property_type, explicit-null PATCH
rejection, and audit-noise suppression for no-op adjustment edits.
"""
from datetime import date

from app.services.adjustments import suggest_adjustments
from app.services.csv_import import parse_comparables_csv

from .test_api_workflow import SUBJECT, create_cma, import_sample

CSV_HEADER = "address,sale_price,sale_date,square_feet,bedrooms,bathrooms"


# --- CSV hardening -----------------------------------------------------------

def test_csv_rejects_non_finite_numbers():
    text = (
        CSV_HEADER + "\n"
        "1 Inf St,Infinity,2026-04-01,1500,3,2\n"
        "2 Nan St,nan,2026-04-01,1500,3,2\n"
        "3 Ok St,900000,2026-04-01,1500,3,2\n"
    )
    rows, errors = parse_comparables_csv(text)
    assert len(rows) == 1
    assert rows[0]["address"] == "3 Ok St"
    assert {e["row"] for e in errors} == {1, 2}
    assert all("finite" in e["message"] for e in errors)


def test_csv_surplus_cells_are_row_errors_not_crashes():
    text = (
        CSV_HEADER + "\n"
        "1 Extra St,900000,2026-04-01,1500,3,2,SURPLUS,MORE\n"
        "2 Ok St,900000,2026-04-01,1500,3,2\n"
    )
    rows, errors = parse_comparables_csv(text)
    assert len(rows) == 1
    assert rows[0]["address"] == "2 Ok St"
    assert errors == [{"row": 1, "field": "row",
                       "message": "Row has more columns than the header"}]


def test_csv_import_endpoint_survives_bad_values(client):
    """The API must return row errors, never a 500, and never commit junk."""
    cma_id = create_cma(client, "Bad CSV values")
    text = (
        CSV_HEADER + "\n"
        "1 Inf St,inf,2026-04-01,1500,3,2\n"
        "2 Extra St,900000,2026-04-01,1500,3,2,surplus\n"
    )
    response = client.post(
        "/api/cmas/%d/comparables/import-csv" % cma_id,
        files={"file": ("bad.csv", text.encode(), "text/csv")})
    assert response.status_code == 200
    assert response.json()["imported_count"] == 0
    assert response.json()["error_count"] == 2
    # The comparables list stays readable afterwards.
    assert client.get("/api/cmas/%d/comparables" % cma_id).status_code == 200


# --- Unknown stays unknown ---------------------------------------------------

class _Prop:
    def __init__(self, **kw):
        self.square_feet = None
        self.lot_size = None
        self.bedrooms = None
        self.bathrooms = None
        self.condition = None
        self.parking_spaces = None
        self.has_pool = None
        self.sale_price = 1_000_000.0
        self.sale_date = date(2026, 7, 1)
        for k, v in kw.items():
            setattr(self, k, v)


def test_pool_adjustment_skipped_when_pool_unknown():
    assumptions = {"pool_value": 25_000.0}
    subject = _Prop(has_pool=True)
    comp_unknown = _Prop(has_pool=None)
    specs = suggest_adjustments(subject, comp_unknown, assumptions,
                                as_of=date(2026, 8, 1))
    assert [s for s in specs if s["category"] == "pool"] == []
    # A known "no pool" still adjusts.
    comp_known = _Prop(has_pool=False)
    specs = suggest_adjustments(subject, comp_known, assumptions,
                                as_of=date(2026, 8, 1))
    assert [s["amount"] for s in specs if s["category"] == "pool"] == [25_000.0]


def test_blank_csv_fields_do_not_create_pool_adjustment(client):
    cma_id = create_cma(client, "Unknown pool")
    subject = dict(SUBJECT, has_pool=True)
    client.put("/api/cmas/%d/subject" % cma_id, json=subject)
    text = CSV_HEADER + "\n1 Mystery St,900000,2026-04-01,1500,3,2\n"
    response = client.post(
        "/api/cmas/%d/comparables/import-csv" % cma_id,
        files={"file": ("min.csv", text.encode(), "text/csv")})
    assert response.json()["imported_count"] == 1
    comp = response.json()["comparables"][0]
    assert comp["has_pool"] is None
    assert comp["property_type"] is None
    response = client.post("/api/cmas/%d/adjustments/suggest" % cma_id)
    comp = response.json()[0]
    assert [a for a in comp["adjustments"] if a["category"] == "pool"] == []


# --- Configuration validation ------------------------------------------------

def test_config_rejects_unknown_keys(client):
    cma_id = create_cma(client, "Config unknown key")
    response = client.put("/api/cmas/%d/config" % cma_id,
                          json={"reconciliation": {"typo_key": 1.0}})
    assert response.status_code == 422


def test_config_rejects_negative_range_k(client):
    cma_id = create_cma(client, "Config negative k")
    response = client.put("/api/cmas/%d/config" % cma_id,
                          json={"reconciliation": {"range_k": -1.0}})
    assert response.status_code == 422


def test_config_rejects_negative_dollar_assumptions(client):
    cma_id = create_cma(client, "Config negative assumption")
    response = client.put("/api/cmas/%d/config" % cma_id,
                          json={"assumptions": {"gla_per_sqft": -150.0}})
    assert response.status_code == 422
    # A negative market rate is legitimate (declining market).
    response = client.put("/api/cmas/%d/config" % cma_id,
                          json={"assumptions": {"monthly_market_pct": -0.002}})
    assert response.status_code == 200


def test_config_rejects_non_finite_values(client):
    cma_id = create_cma(client, "Config NaN")
    response = client.put("/api/cmas/%d/config" % cma_id,
                          json={"assumptions": {"gla_per_sqft": "NaN"}})
    assert response.status_code == 422


def test_config_rejects_nonpositive_similarity_params(client):
    cma_id = create_cma(client, "Config zero cap")
    response = client.put("/api/cmas/%d/config" % cma_id,
                          json={"similarity_params": {"bedroom_cap": 0}})
    assert response.status_code == 422


# --- Explicit-null PATCH protection ------------------------------------------

def test_patch_null_on_required_fields_is_422(client):
    cma_id = create_cma(client, "Null patch")
    client.put("/api/cmas/%d/subject" % cma_id, json=SUBJECT)
    import_sample(client, cma_id)
    comp = client.get("/api/cmas/%d/comparables" % cma_id).json()[0]

    assert client.patch("/api/comparables/%d" % comp["id"],
                        json={"sale_price": None}).status_code == 422
    assert client.patch("/api/cmas/%d" % cma_id,
                        json={"title": None}).status_code == 422
    # PATCH must also respect the future-sale-date rule from create.
    assert client.patch("/api/comparables/%d" % comp["id"],
                        json={"sale_date": "2099-01-01"}).status_code == 422
    assert client.post("/api/comparables/%d/selection" % comp["id"],
                       json={"included": None}).status_code == 422


def test_adjustment_noop_patch_creates_no_audit_event(client):
    cma_id = create_cma(client, "No-op patch")
    client.put("/api/cmas/%d/subject" % cma_id, json=SUBJECT)
    import_sample(client, cma_id)
    client.post("/api/cmas/%d/adjustments/suggest" % cma_id)
    comps = client.get("/api/cmas/%d/comparables" % cma_id).json()
    adj = next(c for c in comps if c["adjustments"])["adjustments"][0]

    before = len(client.get("/api/cmas/%d/audit" % cma_id).json())
    response = client.patch("/api/adjustments/%d" % adj["id"],
                            json={"amount": adj["amount"]})
    assert response.status_code == 200
    # Unchanged amount: still the original source, no new audit event.
    assert response.json()["source"] == adj["source"]
    assert len(client.get("/api/cmas/%d/audit" % cma_id).json()) == before
    assert client.patch("/api/adjustments/%d" % adj["id"],
                        json={"amount": None}).status_code == 422


# --- Staleness and the report consistency gate -------------------------------

def _prepare_valued_cma(client):
    cma_id = create_cma(client, "Staleness test")
    client.put("/api/cmas/%d/subject" % cma_id, json=SUBJECT)
    import_sample(client, cma_id)
    client.post("/api/cmas/%d/adjustments/suggest" % cma_id)
    response = client.post("/api/cmas/%d/valuation/recalculate" % cma_id)
    assert response.status_code == 200
    return cma_id


def test_fresh_valuation_is_not_stale(client):
    cma_id = _prepare_valued_cma(client)
    valuation = client.get("/api/cmas/%d/valuation" % cma_id).json()
    assert valuation["stale"] is False
    assert valuation["effective_count"] == valuation["included_count"]


def test_input_changes_mark_valuation_stale(client):
    cma_id = _prepare_valued_cma(client)
    comp = client.get("/api/cmas/%d/comparables" % cma_id).json()[0]
    client.patch("/api/comparables/%d" % comp["id"], json={"sale_price": 999_999})
    assert client.get("/api/cmas/%d/valuation" % cma_id).json()["stale"] is True
    # The CMA summary carries the same flag for the UI.
    summary = client.get("/api/cmas/%d" % cma_id).json()
    assert summary["latest_valuation"]["stale"] is True
    # Recalculating clears it.
    client.post("/api/cmas/%d/valuation/recalculate" % cma_id)
    assert client.get("/api/cmas/%d/valuation" % cma_id).json()["stale"] is False


def test_assumption_changes_mark_valuation_stale(client):
    cma_id = _prepare_valued_cma(client)
    client.put("/api/cmas/%d/config" % cma_id,
               json={"assumptions": {"gla_per_sqft": 200.0}})
    assert client.get("/api/cmas/%d/valuation" % cma_id).json()["stale"] is True


def test_cosmetic_changes_do_not_mark_stale(client):
    cma_id = _prepare_valued_cma(client)
    client.patch("/api/cmas/%d" % cma_id, json={"title": "Renamed CMA"})
    comp = client.get("/api/cmas/%d/comparables" % cma_id).json()[0]
    client.patch("/api/comparables/%d" % comp["id"], json={"notes": "nice street"})
    assert client.get("/api/cmas/%d/valuation" % cma_id).json()["stale"] is False


def test_report_blocked_until_outputs_are_consistent(client):
    cma_id = _prepare_valued_cma(client)
    client.post("/api/cmas/%d/strategies/generate" % cma_id)
    # Consistent state: report succeeds.
    assert client.post("/api/cmas/%d/report" % cma_id).status_code == 201

    # Change an input: the report is now blocked.
    comp = client.get("/api/cmas/%d/comparables" % cma_id).json()[0]
    client.patch("/api/comparables/%d" % comp["id"], json={"sale_price": 888_888})
    response = client.post("/api/cmas/%d/report" % cma_id)
    assert response.status_code == 409
    assert "Recalculate" in response.json()["detail"]

    # Recalculate only: the suggestions were derived from the old sale price
    # (and the strategies from the old valuation), so the report stays blocked.
    client.post("/api/cmas/%d/valuation/recalculate" % cma_id)
    response = client.post("/api/cmas/%d/report" % cma_id)
    assert response.status_code == 409

    # Full repair chain: regenerate suggestions, recalculate, refresh
    # strategies. Only then is the report consistent again.
    client.post("/api/cmas/%d/adjustments/suggest" % cma_id)
    client.post("/api/cmas/%d/valuation/recalculate" % cma_id)
    client.post("/api/cmas/%d/strategies/generate" % cma_id)
    assert client.post("/api/cmas/%d/report" % cma_id).status_code == 201


# --- Second audit round: provenance, bounds, completeness --------------------

def test_outdated_suggestions_flagged_and_block_report(client):
    """Changing assumptions without regenerating suggestions must not produce
    a 'fresh' valuation from stale suggested amounts."""
    cma_id = _prepare_valued_cma(client)
    client.post("/api/cmas/%d/strategies/generate" % cma_id)
    assert client.post("/api/cmas/%d/report" % cma_id).status_code == 201

    # Change an assumption but do NOT regenerate suggestions.
    client.put("/api/cmas/%d/config" % cma_id,
               json={"assumptions": {"gla_per_sqft": 300.0}})
    config = client.get("/api/cmas/%d/config" % cma_id).json()
    assert config["suggestions_outdated"] is True

    # Recalculating makes the fingerprint current, but the valuation must
    # carry the provenance warning and the report must stay blocked.
    valuation = client.post("/api/cmas/%d/valuation/recalculate" % cma_id).json()
    codes = [w["code"] for w in valuation["warnings"]]
    assert "outdated_suggestions" in codes
    response = client.post("/api/cmas/%d/report" % cma_id)
    assert response.status_code == 409
    assert "assumption set" in response.json()["detail"]

    # Regenerating suggestions clears the flag and unblocks the chain.
    client.post("/api/cmas/%d/adjustments/suggest" % cma_id)
    assert client.get("/api/cmas/%d/config" % cma_id).json()[
        "suggestions_outdated"] is False
    valuation = client.post("/api/cmas/%d/valuation/recalculate" % cma_id).json()
    assert "outdated_suggestions" not in [w["code"] for w in valuation["warnings"]]
    client.post("/api/cmas/%d/strategies/generate" % cma_id)
    assert client.post("/api/cmas/%d/report" % cma_id).status_code == 201


def test_incomplete_cma_cannot_generate_report(client):
    cma_id = create_cma(client, "Subject-only report")
    client.put("/api/cmas/%d/subject" % cma_id, json=SUBJECT)
    # No valuation yet.
    response = client.post("/api/cmas/%d/report" % cma_id)
    assert response.status_code == 400
    assert "valuation" in response.json()["detail"].lower()
    # Valuation but no strategies.
    import_sample(client, cma_id)
    client.post("/api/cmas/%d/valuation/recalculate" % cma_id)
    response = client.post("/api/cmas/%d/report" % cma_id)
    assert response.status_code == 400
    assert "strategies" in response.json()["detail"].lower()


def test_extreme_amounts_are_rejected(client):
    cma_id = _prepare_valued_cma(client)
    comp = client.get("/api/cmas/%d/comparables" % cma_id).json()[0]
    # Beyond the +/- $1B bound: rejected before it can overflow anything.
    response = client.post("/api/comparables/%d/adjustments" % comp["id"],
                           json={"category": "other", "amount": 1e12})
    assert response.status_code == 422
    response = client.patch("/api/comparables/%d" % comp["id"],
                            json={"sale_price": 1e12})
    assert response.status_code == 422


def test_csv_rejects_absurd_prices():
    text = CSV_HEADER + "\n1 Big St,2000000000,2026-04-01,1500,3,2\n"
    rows, errors = parse_comparables_csv(text)
    assert rows == []
    assert errors[0]["field"] == "sale_price"
    assert "at most" in errors[0]["message"]


def test_negative_central_estimate_blocks_strategies(client):
    cma_id = create_cma(client, "Negative central")
    client.put("/api/cmas/%d/subject" % cma_id, json=SUBJECT)
    text = CSV_HEADER + "\n1 Cheap St,1000000,2026-04-01,1500,3,2\n"
    client.post("/api/cmas/%d/comparables/import-csv" % cma_id,
                files={"file": ("one.csv", text.encode(), "text/csv")})
    comp = client.get("/api/cmas/%d/comparables" % cma_id).json()[0]
    # A within-bounds but absurd downward adjustment drives the value negative.
    client.post("/api/comparables/%d/adjustments" % comp["id"],
                json={"category": "other", "amount": -900_000_000})
    valuation = client.post("/api/cmas/%d/valuation/recalculate" % cma_id).json()
    assert valuation["central_estimate"] < 0
    assert "nonpositive_estimate" in [w["code"] for w in valuation["warnings"]]
    # No negative list prices can be generated from it.
    assert client.post("/api/cmas/%d/strategies/generate" % cma_id).status_code == 400


def test_strategies_record_their_source_valuation(client):
    cma_id = _prepare_valued_cma(client)
    valuation = client.get("/api/cmas/%d/valuation" % cma_id).json()
    strategies = client.post("/api/cmas/%d/strategies/generate" % cma_id).json()
    assert all(s["valuation_id"] == valuation["id"] for s in strategies)
    # Regenerating after a recalculation re-links to the new valuation.
    new_valuation = client.post("/api/cmas/%d/valuation/recalculate" % cma_id).json()
    strategies = client.post("/api/cmas/%d/strategies/generate" % cma_id).json()
    assert all(s["valuation_id"] == new_valuation["id"] for s in strategies)


# --- Third audit round: full suggestion provenance, caps, stale gates --------

def test_subject_edit_marks_suggestions_outdated(client):
    """Suggested amounts derive from subject fields too: resizing the subject
    must invalidate them, not just assumption changes."""
    cma_id = _prepare_valued_cma(client)
    client.post("/api/cmas/%d/strategies/generate" % cma_id)
    assert client.post("/api/cmas/%d/report" % cma_id).status_code == 201

    client.put("/api/cmas/%d/subject" % cma_id, json=dict(SUBJECT, square_feet=2400))
    assert client.get("/api/cmas/%d/config" % cma_id).json()[
        "suggestions_outdated"] is True
    valuation = client.post("/api/cmas/%d/valuation/recalculate" % cma_id).json()
    assert "outdated_suggestions" in [w["code"] for w in valuation["warnings"]]
    assert client.post("/api/cmas/%d/report" % cma_id).status_code == 409

    # The full repair chain unblocks it.
    client.post("/api/cmas/%d/adjustments/suggest" % cma_id)
    client.post("/api/cmas/%d/valuation/recalculate" % cma_id)
    client.post("/api/cmas/%d/strategies/generate" % cma_id)
    assert client.post("/api/cmas/%d/report" % cma_id).status_code == 201


def test_new_comparable_marks_suggestions_outdated(client):
    cma_id = _prepare_valued_cma(client)
    text = CSV_HEADER + "\n1 Newcomer St,1000000,2026-05-01,1600,3,2\n"
    client.post("/api/cmas/%d/comparables/import-csv" % cma_id,
                files={"file": ("new.csv", text.encode(), "text/csv")})
    assert client.get("/api/cmas/%d/config" % cma_id).json()[
        "suggestions_outdated"] is True


def test_stale_valuation_blocks_strategy_generation(client):
    cma_id = _prepare_valued_cma(client)
    comp = client.get("/api/cmas/%d/comparables" % cma_id).json()[0]
    client.patch("/api/comparables/%d" % comp["id"], json={"sale_price": 777_777})
    response = client.post("/api/cmas/%d/strategies/generate" % cma_id)
    assert response.status_code == 409
    assert "Recalculate" in response.json()["detail"]
    client.post("/api/cmas/%d/valuation/recalculate" % cma_id)
    assert client.post("/api/cmas/%d/strategies/generate" % cma_id).status_code == 200


def test_extreme_assumptions_and_subject_are_rejected(client):
    cma_id = create_cma(client, "Extremes")
    assert client.put("/api/cmas/%d/config" % cma_id,
                      json={"assumptions": {"gla_per_sqft": 1e12}}).status_code == 422
    assert client.put(
        "/api/cmas/%d/config" % cma_id,
        json={"similarity_params": {"bedroom_cap": 1e12}}).status_code == 422
    big_subject = dict(SUBJECT, square_feet=1e12)
    assert client.put("/api/cmas/%d/subject" % cma_id,
                      json=big_subject).status_code == 422


def test_subject_unknowns_never_guessed(client):
    cma_id = create_cma(client, "Unknown subject")
    response = client.put("/api/cmas/%d/subject" % cma_id,
                          json={"address": "1 Mystery Manor"})
    assert response.status_code == 200
    subject = response.json()
    assert subject["property_type"] is None
    assert subject["has_pool"] is None
