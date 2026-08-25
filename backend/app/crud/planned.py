import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.planned import PlannedWorkout
from app.schemas.planned import PlannedWorkoutIn, PlannedWorkoutUpdate, WeekPlanReplace


def list_planned(
    db: Session, user_id: int, start: datetime.date, end: datetime.date
) -> list[PlannedWorkout]:
    return list(
        db.scalars(
            select(PlannedWorkout)
            .where(
                PlannedWorkout.user_id == user_id,
                PlannedWorkout.date >= start,
                PlannedWorkout.date <= end,
            )
            .order_by(PlannedWorkout.date)
        )
    )


def get_for_date(db: Session, user_id: int, date: datetime.date) -> PlannedWorkout | None:
    return db.scalar(
        select(PlannedWorkout).where(PlannedWorkout.user_id == user_id, PlannedWorkout.date == date)
    )


def get_planned(db: Session, user_id: int, planned_id: int) -> PlannedWorkout | None:
    row = db.get(PlannedWorkout, planned_id)
    return row if row is not None and row.user_id == user_id else None


def upsert(db: Session, user_id: int, data: PlannedWorkoutIn) -> PlannedWorkout:
    existing = get_for_date(db, user_id, data.date)
    if existing is None:
        existing = PlannedWorkout(user_id=user_id, date=data.date)
        db.add(existing)
    existing.workout_type = data.workout_type
    existing.title = data.title
    existing.details = data.details
    existing.source = data.source
    db.commit()
    db.refresh(existing)
    return existing


def update(db: Session, planned: PlannedWorkout, data: PlannedWorkoutUpdate) -> PlannedWorkout:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(planned, field, value)
    planned.source = "manual"  # editar a mano lo marca como manual
    db.commit()
    db.refresh(planned)
    return planned


def delete_planned(db: Session, planned: PlannedWorkout) -> None:
    db.delete(planned)
    db.commit()


def replace_week(db: Session, user_id: int, data: WeekPlanReplace) -> list[PlannedWorkout]:
    """Borra los 7 días desde `week_start` e inserta el nuevo plan de la semana."""
    week_end = data.week_start + datetime.timedelta(days=6)
    db.execute(
        delete(PlannedWorkout).where(
            PlannedWorkout.user_id == user_id,
            PlannedWorkout.date >= data.week_start,
            PlannedWorkout.date <= week_end,
        )
    )
    created = []
    for day in data.days:
        if not (data.week_start <= day.date <= week_end):
            continue  # ignora días fuera de la semana indicada
        row = PlannedWorkout(
            user_id=user_id,
            date=day.date,
            workout_type=day.workout_type,
            title=day.title,
            details=day.details,
            source=data.source,  # todos los días heredan el origen de la semana (p. ej. "ai")
        )
        db.add(row)
        created.append(row)
    db.commit()
    for row in created:
        db.refresh(row)
    return created
