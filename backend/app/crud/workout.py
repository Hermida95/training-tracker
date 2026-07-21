import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.workout import (
    ExerciseTemplate,
    WorkoutExercise,
    WorkoutSession,
    WorkoutSet,
    WorkoutType,
)
from app.schemas.workout import WorkoutSessionCreate
from app.utils.periodization import compute_cycle_week


def list_exercise_templates(
    db: Session, user_id: int, workout_type: WorkoutType | None = None
) -> list[ExerciseTemplate]:
    stmt = (
        select(ExerciseTemplate)
        .where(ExerciseTemplate.user_id == user_id)
        .order_by(ExerciseTemplate.workout_type, ExerciseTemplate.order)
    )
    if workout_type:
        stmt = stmt.where(ExerciseTemplate.workout_type == workout_type)
    return list(db.scalars(stmt))


def _session_query(user_id: int):
    return (
        select(WorkoutSession)
        .where(WorkoutSession.user_id == user_id)
        .options(selectinload(WorkoutSession.exercises).selectinload(WorkoutExercise.sets))
    )


def list_sessions(
    db: Session,
    user_id: int,
    workout_type: WorkoutType | None = None,
    start: datetime.date | None = None,
    end: datetime.date | None = None,
    limit: int | None = None,
) -> list[WorkoutSession]:
    stmt = _session_query(user_id).order_by(WorkoutSession.date.desc(), WorkoutSession.id.desc())
    if workout_type:
        stmt = stmt.where(WorkoutSession.workout_type == workout_type)
    if start:
        stmt = stmt.where(WorkoutSession.date >= start)
    if end:
        stmt = stmt.where(WorkoutSession.date <= end)
    if limit:
        stmt = stmt.limit(limit)
    return list(db.scalars(stmt))


def get_session(db: Session, user_id: int, session_id: int) -> WorkoutSession | None:
    return db.scalar(_session_query(user_id).where(WorkoutSession.id == session_id))


def get_previous_session(
    db: Session,
    user_id: int,
    workout_type: WorkoutType,
    before_date: datetime.date,
    exclude_id: int | None = None,
) -> WorkoutSession | None:
    stmt = (
        _session_query(user_id)
        .where(WorkoutSession.workout_type == workout_type, WorkoutSession.date < before_date)
        .order_by(WorkoutSession.date.desc(), WorkoutSession.id.desc())
        .limit(1)
    )
    if exclude_id:
        stmt = stmt.where(WorkoutSession.id != exclude_id)
    return db.scalar(stmt)


def create_session(db: Session, user_id: int, data: WorkoutSessionCreate) -> WorkoutSession:
    session = WorkoutSession(
        user_id=user_id,
        date=data.date,
        workout_type=data.workout_type,
        notes=data.notes,
        running_minutes=data.running_minutes,
        running_feeling=data.running_feeling,
        cycle_week=compute_cycle_week(db, user_id, data.date),
    )
    for ex_in in data.exercises:
        exercise = WorkoutExercise(
            name=ex_in.name,
            order=ex_in.order,
            exercise_template_id=ex_in.exercise_template_id,
        )
        for set_in in ex_in.sets:
            exercise.sets.append(
                WorkoutSet(
                    set_number=set_in.set_number,
                    weight_kg=set_in.weight_kg,
                    reps=set_in.reps,
                    rir=set_in.rir,
                )
            )
        session.exercises.append(exercise)

    db.add(session)
    db.commit()
    db.refresh(session)
    return get_session(db, user_id, session.id)  # reload with eager-loaded relationships


def delete_session(db: Session, session: WorkoutSession) -> None:
    db.delete(session)
    db.commit()
