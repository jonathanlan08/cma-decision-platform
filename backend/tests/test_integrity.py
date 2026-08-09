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

    # Recalculate only: strategies are still from the old valuation.
    client.post("/api/cmas/%d/valuation/recalculate" % cma_id)
    response = client.post("/api/cmas/%d/report" % cma_id)
    assert response.status_code == 409
    assert "strategies" in response.json()["detail"].lower()

    # Regenerate strategies: the full chain is consistent again.
    client.post("/api/cmas/%d/strategies/generate" % cma_id)
    assert client.post("/api/cmas/%d/report" % cma_id).status_code == 201
