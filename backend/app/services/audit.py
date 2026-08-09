"""Audit trail helper. Every mutating operation calls log_event with a
plain-language summary a non-technical reader can follow, plus structured
details for inspection. Events are append-only."""
from typing import Optional

from sqlalchemy.orm import Session

from ..constants import CALC_VERSION
from ..models import AuditEvent


def log_event(
    db: Session,
    cma_id: int,
    event_type: str,
    summary: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    details: Optional[dict] = None,
    actor: str = "demo",
) -> AuditEvent:
    event = AuditEvent(
        cma_id=cma_id,
        actor=actor,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary,
        details=details,
        calc_version=CALC_VERSION,
    )
    db.add(event)
    return event
