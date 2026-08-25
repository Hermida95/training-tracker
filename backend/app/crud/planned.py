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


def move(db: Session, planned: PlannedWorkout, to_date: datetime.date) -> list[PlannedWorkout]:
    """Mueve `planned` a `to_date`.

    Si ese día ya tiene un plan, intercambia el CONTENIDO entre ambas filas
    (cada una conserva su propio id y su propia fecha) en vez de tocar
    `date`, para no chocar nunca con la unique constraint (user_id, date).
    Si el día está libre, simplemente mueve la fila; el día de origen queda
    sin plan (descanso implícito, como ya trata la app en cualquier hueco).
    """
    if planned.date == to_date:
        return [planned]

    target = get_for_date(db, planned.user_id, to_date)
    if target is None:
        planned.date = to_date
        planned.source = "manual"
        db.commit()
        db.refresh(planned)
        return [planned]

    planned.workout_type, target.workout_type = target.workout_type, planned.workout_type
    planned.title, target.title = target.title, planned.title
    planned.details, target.details = target.details, planned.details
    planned.source = "manual"
    target.source = "manual"
    db.commit()
    db.refresh(planned)
    db.refresh(target)
    return [planned, target]


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
