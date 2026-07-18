import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.break_event import BreakEvent, BreakStatus
from app.schemas.break_event import BreakEventCreate


def list_breaks(
    db: Session, start: datetime.datetime | None = None, end: datetime.datetime | None = None
) -> list[BreakEvent]:
    stmt = select(BreakEvent).order_by(BreakEvent.scheduled_for)
    if start:
        stmt = stmt.where(BreakEvent.scheduled_for >= start)
    if end:
        stmt = stmt.where(BreakEvent.scheduled_for <= end)
    return list(db.scalars(stmt))


def get_break(db: Session, break_id: int) -> BreakEvent | None:
    return db.get(BreakEvent, break_id)


def create_break(db: Session, data: BreakEventCreate) -> BreakEvent:
    event = BreakEvent(scheduled_for=data.scheduled_for)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def mark_done(db: Session, event: BreakEvent) -> BreakEvent:
    event.status = BreakStatus.DONE
    event.responded_at = datetime.datetime.now(datetime.UTC)
    db.commit()
    db.refresh(event)
    return event


def postpone(db: Session, event: BreakEvent, minutes: int = 5) -> BreakEvent:
    """Marca la actual como pospuesta y crea una nueva pausa `minutes` más tarde."""
    event.status = BreakStatus.POSTPONED
    event.responded_at = datetime.datetime.now(datetime.UTC)

    new_event = BreakEvent(
        scheduled_for=event.scheduled_for + datetime.timedelta(minutes=minutes),
        postponed_from_id=event.id,
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return new_event
