"""Shared fixtures. A temp-file SQLite DB isolates every test from dev data;
factory helpers build plain subject/comparable objects for pure-function tests."""
import os
import tempfile
from datetime import date
from types import SimpleNamespace

import pytest

# Must be set before any app import so the engine binds to the test database.
_TMPDIR = tempfile.mkdtemp(prefix="cma-test-")
os.environ["DATABASE_URL"] = "sqlite:///%s/test.db" % _TMPDIR

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

AS_OF = date(2026, 8, 1)


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


def make_subject(**overrides):
    base = {
        "address": "12345 Demo Lane",
        "latitude": None,
        "longitude": None,
        "property_type": "single_family",
        "bedrooms": 3,
        "bathrooms": 2.0,
        "square_feet": 2000.0,
        "lot_size": 6000.0,
        "year_built": 1960,
        "condition": "good",
        "parking_spaces": 2,
        "has_pool": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def make_comp(**overrides):
    base = {
        "address": "999 Sample St",
        "latitude": None,
        "longitude": None,
        "distance_from_subject": 0.0,
        "property_type": "single_family",
        "bedrooms": 3,
        "bathrooms": 2.0,
        "square_feet": 2000.0,
        "lot_size": 6000.0,
        "year_built": 1960,
        "condition": "good",
        "parking_spaces": 2,
        "has_pool": False,
        "sale_price": 1_000_000.0,
        "sale_date": AS_OF,
    }
    base.update(overrides)
    return SimpleNamespace(**base)
