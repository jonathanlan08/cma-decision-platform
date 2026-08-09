"""Seed the database with a complete synthetic demo CMA.

Run from backend/:  python -m app.seed
Idempotent: skips seeding if the demo CMA already exists.

All data is synthetic (see data/sample/README.md): no real sales, clients,
or confidential information.
"""
from pathlib import Path

from .constants import CALC_VERSION
from .database import Base, SessionLocal, engine
from .models import Adjustment, CMAAnalysis, ComparableProperty, SubjectProperty, User
from .routers.helpers import ensure_config, ensure_selection, refresh_similarity
from .services.adjustments import suggest_adjustments
from .services.audit import log_event

DEMO_TITLE = "Demo CMA: 12345 Demo Lane, Arcadia (synthetic data)"
SAMPLE_CSV = Path(__file__).resolve().parents[2] / "data" / "sample" / "comparables_sample.csv"


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(CMAAnalysis).filter(CMAAnalysis.title == DEMO_TITLE).first():
            print("Demo CMA already exists; nothing to do.")
            return

        user = db.query(User).filter(User.email == "demo@example.com").first()
        if user is None:
            user = User(email="demo@example.com", display_name="Demo Agent")
            db.add(user)
            db.flush()

        cma = CMAAnalysis(user_id=user.id, title=DEMO_TITLE, status="draft")
        db.add(cma)
        db.flush()
        config = ensure_config(db, cma)
        log_event(db, cma.id, "cma_created", "Created CMA analysis '%s'." % cma.title,
                  actor="seed-script")

        cma.subject = SubjectProperty(
            cma_id=cma.id,
            address="12345 Demo Lane",
            city="Arcadia",
            zip_code="91006",
            latitude=34.1340,
            longitude=-118.0390,
            property_type="single_family",
            bedrooms=3,
            bathrooms=2.0,
            square_feet=1850,
            lot_size=7200,
            year_built=1958,
            condition="good",
            parking_spaces=2,
            has_pool=False,
            renovation_notes="Kitchen refreshed 2024; original hardwood floors (synthetic demo).",
            agent_notes="Synthetic demonstration subject property.",
        )
        db.add(cma.subject)
        log_event(db, cma.id, "subject_created",
                  "Entered subject property 12345 Demo Lane.", actor="seed-script")

        from .services.csv_import import parse_comparables_csv
        rows, errors = parse_comparables_csv(SAMPLE_CSV.read_text())
        if errors:
            raise RuntimeError("Sample CSV failed validation: %s" % errors)
        for row in rows:
            comp = ComparableProperty(cma_id=cma.id, **row)
            db.add(comp)
            db.flush()
            ensure_selection(db, comp)
        log_event(db, cma.id, "csv_imported",
                  "Imported %d synthetic comparables from the bundled sample CSV."
                  % len(rows), actor="seed-script")

        refresh_similarity(db, cma)
        log_event(db, cma.id, "similarity_recalculated",
                  "Calculated similarity scores for %d comparables." % len(rows),
                  actor="seed-script")

        total = 0
        for comp in cma.comparables:
            for spec in suggest_adjustments(cma.subject, comp, config.assumptions):
                db.add(Adjustment(comparable_id=comp.id, source="suggested", **spec))
                total += 1
        log_event(db, cma.id, "adjustments_suggested",
                  "Generated %d suggested adjustments from the default sample "
                  "assumption set." % total, actor="seed-script")
        db.commit()

        # Reuse the API-layer recalculation for valuation + strategies so the
        # seeded analysis matches exactly what the endpoints would produce.
        from fastapi.testclient import TestClient

        from .main import app
        client = TestClient(app)
        response = client.post("/api/cmas/%d/valuation/recalculate" % cma.id)
        response.raise_for_status()
        client.post("/api/cmas/%d/strategies/generate" % cma.id).raise_for_status()

        valuation = response.json()
        print("Seeded '%s' (%s)" % (DEMO_TITLE, CALC_VERSION))
        print("  comparables: %d   central estimate: $%s   range: $%s – $%s" % (
            len(rows),
            format(round(valuation["central_estimate"]), ","),
            format(round(valuation["low_estimate"]), ","),
            format(round(valuation["high_estimate"]), ","),
        ))
    finally:
        db.close()


if __name__ == "__main__":
    seed()
