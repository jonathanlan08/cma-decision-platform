"""CMA analysis CRUD, subject property, and per-CMA configuration."""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CMAAnalysis, SubjectProperty, User
from ..schemas import (
    CMACreate,
    CMADetail,
    CMASummary,
    CMAUpdate,
    ConfigOut,
    ConfigUpdate,
    SubjectIn,
    SubjectOut,
)
from ..services.audit import log_event
from .helpers import (
    ensure_config,
    get_cma_or_404,
    latest_valuation,
    suggestions_outdated,
    touch,
    valuation_out,
)


def _config_out(cma: CMAAnalysis, config) -> ConfigOut:
    out = ConfigOut.model_validate(config)
    out.suggestions_outdated = suggestions_outdated(cma, config)
    return out

router = APIRouter(prefix="/api/cmas", tags=["CMA analyses"])


def _demo_user(db: Session) -> User:
    user = db.query(User).order_by(User.id).first()
    if user is None:
        user = User(email="demo@example.com", display_name="Demo Agent")
        db.add(user)
        db.flush()
    return user


def _summary(cma: CMAAnalysis) -> CMASummary:
    valuation = latest_valuation(cma)
    return CMASummary(
        id=cma.id,
        title=cma.title,
        status=cma.status,
        created_at=cma.created_at,
        updated_at=cma.updated_at,
        subject_address=cma.subject.address if cma.subject else None,
        comparable_count=len(cma.comparables),
        included_count=sum(
            1 for c in cma.comparables if c.selection is not None and c.selection.included
        ),
        strategy_count=len(cma.strategies),
        report_count=len(cma.reports),
        latest_valuation=valuation_out(cma, valuation) if valuation else None,
    )


@router.get("", response_model=List[CMASummary])
def list_cmas(db: Session = Depends(get_db)):
    cmas = db.query(CMAAnalysis).order_by(CMAAnalysis.updated_at.desc()).all()
    return [_summary(cma) for cma in cmas]


@router.post("", response_model=CMADetail, status_code=201)
def create_cma(payload: CMACreate, db: Session = Depends(get_db)):
    user = _demo_user(db)
    cma = CMAAnalysis(user_id=user.id, title=payload.title)
    db.add(cma)
    db.flush()
    ensure_config(db, cma)
    log_event(db, cma.id, "cma_created", "Created CMA analysis '%s'." % cma.title)
    db.commit()
    db.refresh(cma)
    return _detail(cma)


def _detail(cma: CMAAnalysis) -> CMADetail:
    base = _summary(cma).model_dump()
    base.update({
        "notes": cma.notes,
        "subject": SubjectOut.model_validate(cma.subject) if cma.subject else None,
    })
    return CMADetail(**base)


@router.get("/{cma_id}", response_model=CMADetail)
def get_cma(cma_id: int, db: Session = Depends(get_db)):
    return _detail(get_cma_or_404(db, cma_id))


@router.patch("/{cma_id}", response_model=CMADetail)
def update_cma(cma_id: int, payload: CMAUpdate, db: Session = Depends(get_db)):
    cma = get_cma_or_404(db, cma_id)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(cma, field, value)
    if changes:
        log_event(
            db, cma.id, "cma_updated",
            "Updated CMA settings: %s." % ", ".join(sorted(changes)),
            details={"changes": {k: str(v) for k, v in changes.items()}},
        )
    db.commit()
    db.refresh(cma)
    return _detail(cma)


@router.put("/{cma_id}/subject", response_model=SubjectOut)
def upsert_subject(cma_id: int, payload: SubjectIn, db: Session = Depends(get_db)):
    cma = get_cma_or_404(db, cma_id)
    data = payload.model_dump()
    if cma.subject is None:
        cma.subject = SubjectProperty(cma_id=cma.id, **data)
        db.add(cma.subject)
        log_event(db, cma.id, "subject_created",
                  "Entered subject property %s." % payload.address,
                  entity_type="subject_property")
    else:
        before = {k: getattr(cma.subject, k) for k in data}
        changed = [k for k, v in data.items() if before[k] != v]
        for field, value in data.items():
            setattr(cma.subject, field, value)
        if changed:
            log_event(
                db, cma.id, "subject_updated",
                "Updated subject property fields: %s." % ", ".join(sorted(changed)),
                entity_type="subject_property", entity_id=cma.subject.id,
                details={"changed_fields": {
                    k: {"from": str(before[k]), "to": str(data[k])} for k in changed
                }},
            )
    touch(cma)
    db.commit()
    db.refresh(cma)
    return SubjectOut.model_validate(cma.subject)


@router.get("/{cma_id}/config", response_model=ConfigOut)
def get_config(cma_id: int, db: Session = Depends(get_db)):
    cma = get_cma_or_404(db, cma_id)
    config = ensure_config(db, cma)
    db.commit()
    return _config_out(cma, config)


@router.put("/{cma_id}/config", response_model=ConfigOut)
def update_config(cma_id: int, payload: ConfigUpdate, db: Session = Depends(get_db)):
    cma = get_cma_or_404(db, cma_id)
    config = ensure_config(db, cma)
    changes = payload.model_dump(exclude_unset=True)
    labels = {
        "weights": ("weights_updated", "similarity weights"),
        "similarity_params": ("similarity_params_updated", "similarity parameters"),
        "assumptions": ("assumptions_updated", "adjustment assumptions"),
        "reconciliation": ("reconciliation_updated", "reconciliation parameters"),
    }
    for field, value in changes.items():
        if value is None:
            continue
        before = getattr(config, field)
        merged = dict(before)
        merged.update(value)
        setattr(config, field, merged)
        event_type, label = labels[field]
        changed_keys = [k for k in value if before.get(k) != value[k]]
        if changed_keys:
            log_event(
                db, cma.id, event_type,
                "Changed %s: %s." % (label, ", ".join(sorted(changed_keys))),
                entity_type="weight_configuration", entity_id=config.id,
                details={"changes": {
                    k: {"from": before.get(k), "to": value[k]} for k in changed_keys
                }},
            )
    touch(cma)
    db.commit()
    db.refresh(config)
    return _config_out(cma, config)
