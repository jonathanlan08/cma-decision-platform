"""Report generation/download, audit trail, and platform metadata."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from ..constants import (
    CALC_VERSION,
    CMA_STATUSES,
    CONDITION_SCALE,
    DEFAULT_ASSUMPTIONS,
    DEFAULT_RECONCILIATION,
    DEFAULT_SIMILARITY_PARAMS,
    DEFAULT_WEIGHTS,
    DISCLAIMER,
    PROPERTY_TYPES,
)
from ..database import get_db
from ..models import GeneratedReport
from ..schemas import AuditEventOut, MetaOut, ReportOut
from ..services.audit import log_event
from ..services.report import build_report_context, pdf_from_html, render_report_html
from .helpers import comparable_out, ensure_config, get_cma_or_404, latest_valuation, touch

router = APIRouter(prefix="/api", tags=["Reports & audit"])


@router.get("/meta", response_model=MetaOut)
def get_meta():
    return MetaOut(
        calc_version=CALC_VERSION,
        disclaimer=DISCLAIMER,
        condition_scale=CONDITION_SCALE,
        property_types=PROPERTY_TYPES,
        default_weights=DEFAULT_WEIGHTS,
        default_similarity_params=DEFAULT_SIMILARITY_PARAMS,
        default_assumptions=DEFAULT_ASSUMPTIONS,
        default_reconciliation=DEFAULT_RECONCILIATION,
    )


@router.get("/cmas/{cma_id}/audit", response_model=List[AuditEventOut])
def list_audit_events(
    cma_id: int,
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    cma = get_cma_or_404(db, cma_id)
    events = list(reversed(cma.audit_events))[offset:offset + limit]
    return [AuditEventOut.model_validate(e) for e in events]


def _comparable_report_rows(cma):
    rows = []
    for comp in cma.comparables:
        out = comparable_out(comp, cma.subject)
        rows.append({
            "address": comp.address,
            "city": comp.city,
            "sale_price": comp.sale_price,
            "sale_date": comp.sale_date.isoformat(),
            "square_feet": comp.square_feet,
            "bedrooms": comp.bedrooms,
            "bathrooms": comp.bathrooms,
            "distance": out.effective_distance_miles,
            "similarity": comp.selection.similarity_score if comp.selection else None,
            "included": comp.selection.included if comp.selection else True,
            "exclusion_reason": comp.selection.exclusion_reason if comp.selection else None,
            "adjustments": [
                {
                    "category": a.category,
                    "subject_value": a.subject_value,
                    "comparable_value": a.comparable_value,
                    "unit_description": a.unit_description,
                    "amount": a.amount,
                    "source": a.source,
                }
                for a in comp.adjustments
            ],
            "adjusted_price": out.adjusted_price,
            "adjusted_ppsf": out.adjusted_ppsf,
        })
    return rows


@router.post("/cmas/{cma_id}/report", response_model=ReportOut, status_code=201)
def generate_report(cma_id: int, db: Session = Depends(get_db)):
    cma = get_cma_or_404(db, cma_id)
    if cma.subject is None:
        raise HTTPException(status_code=400,
                            detail="Enter the subject property before generating a report")
    config = ensure_config(db, cma)
    valuation = latest_valuation(cma)
    context = build_report_context(
        cma, _comparable_report_rows(cma), valuation, cma.strategies, config
    )
    html = render_report_html(context)
    pdf_bytes: Optional[bytes] = pdf_from_html(html)

    report = GeneratedReport(
        cma_id=cma.id,
        calc_version=CALC_VERSION,
        format="pdf" if pdf_bytes else "html",
        content_html=html,
    )
    db.add(report)
    db.flush()
    if pdf_bytes:
        from pathlib import Path
        out_dir = Path(__file__).resolve().parents[2] / "generated_reports"
        out_dir.mkdir(exist_ok=True)
        pdf_path = out_dir / ("cma_%d_report_%d.pdf" % (cma.id, report.id))
        pdf_path.write_bytes(pdf_bytes)
        report.pdf_path = str(pdf_path)

    log_event(db, cma.id, "report_generated",
              "Generated the CMA report (%s, methodology %s)."
              % (report.format.upper(), CALC_VERSION),
              entity_type="report", entity_id=report.id)
    touch(cma)
    db.commit()
    db.refresh(report)
    return ReportOut.model_validate(report)


@router.get("/cmas/{cma_id}/reports", response_model=List[ReportOut])
def list_reports(cma_id: int, db: Session = Depends(get_db)):
    cma = get_cma_or_404(db, cma_id)
    return [ReportOut.model_validate(r) for r in cma.reports]


@router.get("/reports/{report_id}/download")
def download_report(report_id: int, db: Session = Depends(get_db)):
    report = db.get(GeneratedReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.format == "pdf" and report.pdf_path:
        from pathlib import Path
        path = Path(report.pdf_path)
        if path.is_file():
            return Response(
                content=path.read_bytes(),
                media_type="application/pdf",
                headers={"Content-Disposition":
                         "attachment; filename=cma_report_%d.pdf" % report.id},
            )
    return HTMLResponse(content=report.content_html)


# CMA_STATUSES imported for OpenAPI docs completeness; re-exported via /api/meta.
_ = CMA_STATUSES
