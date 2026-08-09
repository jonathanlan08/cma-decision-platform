"""Comparable management: manual entry, CSV import, selection, similarity."""
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from ..constants import CSV_MAX_BYTES
from ..database import get_db
from ..models import ComparableProperty
from ..schemas import (
    ComparableIn,
    ComparableOut,
    ComparableUpdate,
    CSVImportResult,
    SelectionUpdate,
)
from ..services.audit import log_event
from ..services.csv_import import parse_comparables_csv, template_csv
from .helpers import (
    comparable_out,
    ensure_selection,
    get_cma_or_404,
    get_comparable_or_404,
    refresh_similarity,
    touch,
)

router = APIRouter(prefix="/api", tags=["Comparables"])


@router.get("/csv-template", response_class=PlainTextResponse)
def download_csv_template():
    return PlainTextResponse(
        template_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=comparables_template.csv"},
    )


@router.get("/cmas/{cma_id}/comparables", response_model=List[ComparableOut])
def list_comparables(cma_id: int, db: Session = Depends(get_db)):
    cma = get_cma_or_404(db, cma_id)
    return [comparable_out(comp, cma.subject) for comp in cma.comparables]


@router.post("/cmas/{cma_id}/comparables", response_model=ComparableOut, status_code=201)
def add_comparable(cma_id: int, payload: ComparableIn, db: Session = Depends(get_db)):
    cma = get_cma_or_404(db, cma_id)
    comp = ComparableProperty(cma_id=cma.id, **payload.model_dump())
    db.add(comp)
    db.flush()
    ensure_selection(db, comp)
    log_event(db, cma.id, "comparable_added",
              "Added comparable %s (manual entry)." % comp.address,
              entity_type="comparable", entity_id=comp.id)
    touch(cma)
    db.commit()
    db.refresh(comp)
    return comparable_out(comp, cma.subject)


@router.post("/cmas/{cma_id}/comparables/import-csv", response_model=CSVImportResult)
async def import_csv(cma_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    cma = get_cma_or_404(db, cma_id)
    raw = await file.read()
    if len(raw) > CSV_MAX_BYTES:
        raise HTTPException(status_code=413, detail="CSV file exceeds the 2 MB limit")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400,
                            detail="File must be UTF-8 encoded CSV") from exc

    rows, errors = parse_comparables_csv(text)
    created = []
    for row in rows:
        comp = ComparableProperty(cma_id=cma.id, **row)
        db.add(comp)
        db.flush()
        ensure_selection(db, comp)
        created.append(comp)

    log_event(
        db, cma.id, "csv_imported",
        "Imported %d comparable(s) from CSV '%s'; %d row(s) had validation errors."
        % (len(created), file.filename or "upload", len(errors)),
        details={"filename": file.filename, "imported": len(created),
                 "errors": errors[:50]},
    )
    touch(cma)
    db.commit()
    return CSVImportResult(
        imported_count=len(created),
        error_count=len(errors),
        comparables=[comparable_out(c, cma.subject) for c in created],
        errors=errors,
    )


@router.patch("/comparables/{comp_id}", response_model=ComparableOut)
def update_comparable(comp_id: int, payload: ComparableUpdate, db: Session = Depends(get_db)):
    comp = get_comparable_or_404(db, comp_id)
    changes = payload.model_dump(exclude_unset=True)
    before = {k: getattr(comp, k) for k in changes}
    for field, value in changes.items():
        setattr(comp, field, value)
    changed = [k for k in changes if before[k] != changes[k]]
    if changed:
        log_event(
            db, comp.cma_id, "comparable_updated",
            "Edited comparable %s: %s." % (comp.address, ", ".join(sorted(changed))),
            entity_type="comparable", entity_id=comp.id,
            details={"changes": {
                k: {"from": str(before[k]), "to": str(changes[k])} for k in changed
            }},
        )
    touch(comp.cma)
    db.commit()
    db.refresh(comp)
    return comparable_out(comp, comp.cma.subject)


@router.delete("/comparables/{comp_id}", status_code=204)
def delete_comparable(comp_id: int, db: Session = Depends(get_db)):
    comp = get_comparable_or_404(db, comp_id)
    cma = comp.cma
    log_event(db, cma.id, "comparable_deleted",
              "Removed comparable %s from the analysis." % comp.address,
              entity_type="comparable", entity_id=comp.id)
    db.delete(comp)
    touch(cma)
    db.commit()


@router.post("/comparables/{comp_id}/selection", response_model=ComparableOut)
def update_selection(comp_id: int, payload: SelectionUpdate, db: Session = Depends(get_db)):
    comp = get_comparable_or_404(db, comp_id)
    selection = ensure_selection(db, comp)
    changes = payload.model_dump(exclude_unset=True)

    if "included" in changes and changes["included"] != selection.included:
        selection.included = changes["included"]
        if selection.included:
            selection.exclusion_reason = None
            log_event(db, comp.cma_id, "comparable_included",
                      "Included comparable %s in the analysis." % comp.address,
                      entity_type="comparable", entity_id=comp.id)
        else:
            selection.exclusion_reason = changes.get("exclusion_reason")
            log_event(db, comp.cma_id, "comparable_excluded",
                      "Excluded comparable %s%s." % (
                          comp.address,
                          " — reason: %s" % changes["exclusion_reason"]
                          if changes.get("exclusion_reason") else "",
                      ),
                      entity_type="comparable", entity_id=comp.id,
                      details={"reason": changes.get("exclusion_reason")})
    elif "exclusion_reason" in changes:
        old_reason = selection.exclusion_reason
        selection.exclusion_reason = changes["exclusion_reason"]
        if not selection.included and old_reason != selection.exclusion_reason:
            log_event(db, comp.cma_id, "exclusion_reason_updated",
                      "Recorded exclusion reason for %s: %s" % (
                          comp.address, selection.exclusion_reason or "(cleared)"),
                      entity_type="comparable", entity_id=comp.id,
                      details={"from": old_reason, "to": selection.exclusion_reason})

    if ("user_weight_multiplier" in changes
            and changes["user_weight_multiplier"] != selection.user_weight_multiplier):
        old = selection.user_weight_multiplier
        selection.user_weight_multiplier = changes["user_weight_multiplier"]
        log_event(db, comp.cma_id, "weight_override",
                  "Set weight multiplier for %s to %.2f (was %.2f). User override."
                  % (comp.address, selection.user_weight_multiplier, old),
                  entity_type="comparable", entity_id=comp.id,
                  details={"from": old, "to": selection.user_weight_multiplier})

    touch(comp.cma)
    db.commit()
    db.refresh(comp)
    return comparable_out(comp, comp.cma.subject)


@router.post("/cmas/{cma_id}/similarity/recalculate", response_model=List[ComparableOut])
def recalculate_similarity(cma_id: int, db: Session = Depends(get_db)):
    cma = get_cma_or_404(db, cma_id)
    count = refresh_similarity(db, cma)
    log_event(db, cma.id, "similarity_recalculated",
              "Recalculated similarity scores for %d comparable(s)." % count)
    touch(cma)
    db.commit()
    return [comparable_out(comp, cma.subject) for comp in cma.comparables]
