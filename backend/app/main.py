"""FastAPI application entry point.

Interactive API documentation: /docs (Swagger UI) and /redoc.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS
from .constants import CALC_VERSION
from .database import Base, engine
from .routers import cmas, comparables, reports, strategies, valuation

app = FastAPI(
    title="CMA Decision Platform API",
    version="0.1.0",
    description=(
        "Transparent Comparative Market Analysis engine. Every valuation is "
        "reproducible from stored inputs: similarity breakdowns, adjustment "
        "math, weights, and an append-only audit trail. Educational project — "
        "not an appraisal tool."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables for the zero-setup SQLite path; Alembic manages real migrations.
Base.metadata.create_all(bind=engine)

app.include_router(cmas.router)
app.include_router(comparables.router)
app.include_router(valuation.router)
app.include_router(strategies.router)
app.include_router(reports.router)


@app.get("/api/health", tags=["Meta"])
def health():
    return {"status": "ok", "calc_version": CALC_VERSION}
