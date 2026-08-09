"""End-to-end API workflow and endpoint validation behavior."""
from pathlib import Path

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "sample" / "comparables_sample.csv"

SUBJECT = {
    "address": "12345 Demo Lane",
    "city": "Arcadia",
    "zip_code": "91006",
    "latitude": 34.1340,
    "longitude": -118.0390,
    "property_type": "single_family",
    "bedrooms": 3,
    "bathrooms": 2.0,
    "square_feet": 1850,
    "lot_size": 7200,
    "year_built": 1958,
    "condition": "good",
    "parking_spaces": 2,
    "has_pool": False,
}


def create_cma(client, title="Workflow test CMA"):
    response = client.post("/api/cmas", json={"title": title})
    assert response.status_code == 201
    return response.json()["id"]


def import_sample(client, cma_id):
    with open(SAMPLE, "rb") as f:
        response = client.post(
            "/api/cmas/%d/comparables/import-csv" % cma_id,
            files={"file": ("comparables_sample.csv", f, "text/csv")},
        )
    assert response.status_code == 200
    return response.json()


def test_full_cma_workflow(client):
    # 1. Create CMA and enter subject
    cma_id = create_cma(client)
    assert client.put("/api/cmas/%d/subject" % cma_id, json=SUBJECT).status_code == 200

    # 2. Upload the sample CSV
    imported = import_sample(client, cma_id)
    assert imported["imported_count"] == 20
    assert imported["error_count"] == 0

    # 3. Similarity scores with full breakdowns
    response = client.post("/api/cmas/%d/similarity/recalculate" % cma_id)
    assert response.status_code == 200
    comps = response.json()
    assert all(c["selection"]["similarity_score"] is not None for c in comps)
    breakdown = comps[0]["selection"]["similarity_breakdown"]
    assert len(breakdown["components"]) == 9

    # 4. Suggested adjustments with documented math
    response = client.post("/api/cmas/%d/adjustments/suggest" % cma_id)
    assert response.status_code == 200
    comps = response.json()
    assert any(c["adjustments"] for c in comps)
    first_adj = next(c for c in comps if c["adjustments"])["adjustments"][0]
    assert first_adj["source"] == "suggested"
    assert first_adj["direction"] in ("upward", "downward")

    # 5. Exclude a distant comp with a reason; boost a close one
    distant = next(c for c in comps if "Rosemead Blvd" in c["address"])
    close = next(c for c in comps if "Placeholder Way" in c["address"])
    response = client.post(
        "/api/comparables/%d/selection" % distant["id"],
        json={"included": False, "exclusion_reason": "Too far from subject"})
    assert response.status_code == 200
    assert response.json()["selection"]["included"] is False
    response = client.post(
        "/api/comparables/%d/selection" % close["id"],
        json={"user_weight_multiplier": 2.0})
    assert response.json()["selection"]["user_weight_multiplier"] == 2.0

    # 6. Manual adjustment + edit a suggested one (becomes manual override)
    response = client.post(
        "/api/comparables/%d/adjustments" % close["id"],
        json={"category": "other", "amount": -10000,
              "explanation": "Backs to busy street"})
    assert response.status_code == 201
    manual_id = response.json()["id"]
    response = client.patch("/api/adjustments/%d" % first_adj["id"],
                            json={"amount": 12345})
    assert response.status_code == 200
    assert response.json()["source"] == "manual"

    # 7. Re-suggesting preserves manual adjustments
    response = client.post("/api/cmas/%d/adjustments/suggest" % cma_id)
    comps = response.json()
    close_after = next(c for c in comps if c["id"] == close["id"])
    manual_kept = [a for a in close_after["adjustments"] if a["id"] == manual_id]
    assert len(manual_kept) == 1

    # 8. Valuation
    response = client.post("/api/cmas/%d/valuation/recalculate" % cma_id)
    assert response.status_code == 200
    valuation = response.json()
    assert valuation["included_count"] == 19
    assert valuation["low_estimate"] < valuation["central_estimate"] < valuation["high_estimate"]
    assert valuation["median_adjusted"] is not None
    assert valuation["weighted_ppsf"] is not None
    influence = sum(e["influence_pct"] for e in valuation["per_comparable"])
    assert abs(influence - 100.0) < 1.0

    # 9. Strategies
    response = client.post("/api/cmas/%d/strategies/generate" % cma_id)
    assert response.status_code == 200
    strategies = response.json()
    assert {s["key"] for s in strategies} == {"market_entry", "competitive", "aspirational"}
    target = next(s for s in strategies if s["key"] == "aspirational")
    response = client.patch("/api/strategies/%d" % target["id"],
                            json={"list_price": target["list_price"] + 50000})
    assert response.status_code == 200
    assert response.json()["is_user_modified"] is True

    # 10. Report
    response = client.post("/api/cmas/%d/report" % cma_id)
    assert response.status_code == 201
    report = response.json()
    download = client.get("/api/reports/%d/download" % report["id"])
    assert download.status_code == 200
    if report["format"] == "html":
        body = download.text
        assert "12345 Demo Lane" in body
        assert "not an appraisal" in body
        assert "Listing Strategy Comparison" in body

    # 11. Audit trail captured everything, in plain language, with calc version
    response = client.get("/api/cmas/%d/audit" % cma_id)
    assert response.status_code == 200
    events = response.json()
    event_types = {e["event_type"] for e in events}
    assert {"cma_created", "subject_created", "csv_imported",
            "similarity_recalculated", "adjustments_suggested",
            "comparable_excluded", "weight_override", "adjustment_added",
            "adjustment_edited", "valuation_recalculated",
            "strategies_generated", "strategy_price_changed",
            "report_generated"} <= event_types
    assert all(e["calc_version"] for e in events)
    exclusion = next(e for e in events if e["event_type"] == "comparable_excluded")
    assert "Too far from subject" in exclusion["summary"]


def test_dashboard_summary_lists_valuation(client):
    cma_id = create_cma(client, "Dashboard test")
    client.put("/api/cmas/%d/subject" % cma_id, json=SUBJECT)
    import_sample(client, cma_id)
    client.post("/api/cmas/%d/valuation/recalculate" % cma_id)
    response = client.get("/api/cmas")
    assert response.status_code == 200
    summary = next(c for c in response.json() if c["id"] == cma_id)
    assert summary["subject_address"] == "12345 Demo Lane"
    assert summary["comparable_count"] == 20
    assert summary["latest_valuation"]["central_estimate"] is not None


def test_valuation_with_no_comparables_reports_warning(client):
    cma_id = create_cma(client, "Empty CMA")
    client.put("/api/cmas/%d/subject" % cma_id, json=SUBJECT)
    response = client.post("/api/cmas/%d/valuation/recalculate" % cma_id)
    assert response.status_code == 200
    valuation = response.json()
    assert valuation["central_estimate"] is None
    assert valuation["included_count"] == 0
    assert valuation["warnings"][0]["code"] == "no_comparables"
    # Strategies cannot be generated without a central estimate
    assert client.post("/api/cmas/%d/strategies/generate" % cma_id).status_code == 400


def test_similarity_requires_subject(client):
    cma_id = create_cma(client, "No subject")
    assert client.post("/api/cmas/%d/similarity/recalculate" % cma_id).status_code == 400


def test_csv_import_reports_row_errors_but_imports_valid(client):
    cma_id = create_cma(client, "CSV errors")
    csv_text = (
        "address,sale_price,sale_date,square_feet,bedrooms,bathrooms\n"
        "1 Ok St,900000,2026-04-01,1500,3,2\n"
        "2 Bad St,-100,2026-04-01,1500,3,2\n"
        "3 Bad St,900000,not-a-date,1500,3,2\n"
    )
    response = client.post(
        "/api/cmas/%d/comparables/import-csv" % cma_id,
        files={"file": ("bad.csv", csv_text.encode(), "text/csv")})
    assert response.status_code == 200
    result = response.json()
    assert result["imported_count"] == 1
    assert result["error_count"] == 2
    rows = {e["row"] for e in result["errors"]}
    assert rows == {2, 3}


def test_validation_errors_are_422(client):
    cma_id = create_cma(client, "Validation")
    bad_subject = dict(SUBJECT, property_type="castle")
    assert client.put("/api/cmas/%d/subject" % cma_id, json=bad_subject).status_code == 422

    future_comp = {
        "address": "1 Future St", "sale_price": 1000000, "sale_date": "2099-01-01",
        "square_feet": 1500, "bedrooms": 3, "bathrooms": 2,
    }
    assert client.post("/api/cmas/%d/comparables" % cma_id,
                       json=future_comp).status_code == 422
    assert client.patch("/api/cmas/%d" % cma_id,
                        json={"status": "bogus"}).status_code == 422


def test_missing_resources_are_404(client):
    assert client.get("/api/cmas/99999").status_code == 404
    assert client.patch("/api/comparables/99999", json={}).status_code == 404
    assert client.get("/api/cmas/99999/audit").status_code == 404


def test_archive_via_status(client):
    cma_id = create_cma(client, "Archive me")
    response = client.patch("/api/cmas/%d" % cma_id, json={"status": "archived"})
    assert response.status_code == 200
    assert response.json()["status"] == "archived"


def test_csv_template_download(client):
    response = client.get("/api/csv-template")
    assert response.status_code == 200
    assert response.text.startswith("address,city,zip_code")
