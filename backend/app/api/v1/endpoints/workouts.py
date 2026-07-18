import datetime

from fastapi import APIRouter, HTTPException

from app.core.deps import DbSession
from app.crud import workout as crud
from app.models.workout import WorkoutType
from app.schemas.workout import (
    ExerciseTemplateRead,
    PeriodizationInfo,
    SessionComparison,
    WorkoutSessionCreate,
    WorkoutSessionRead,
)
from app.utils.comparison import compare_sessions
from app.utils.periodization import compute_cycle_week, get_periodization_info
from app.utils.timezone import today_local

router = APIRouter(prefix="/workouts", tags=["workouts"])


@router.get("/templates", response_model=list[ExerciseTemplateRead])
def list_templates(db: DbSession, workout_type: WorkoutType | None = None):
    return crud.list_exercise_templates(db, workout_type)


@router.get("/periodization", response_model=PeriodizationInfo)
def periodization(db: DbSession, date: datetime.date | None = None):
    cycle_week = compute_cycle_week(db, date or today_local())
    return get_periodization_info(cycle_week)


@router.get("", response_model=list[WorkoutSessionRead])
def list_sessions(
    db: DbSession,
    workout_type: WorkoutType | None = None,
    start: datetime.date | None = None,
    end: datetime.date | None = None,
    limit: int | None = None,
):
    return crud.list_sessions(db, workout_type, start, end, limit)


@router.post("", response_model=WorkoutSessionRead, status_code=201)
def create_session(data: WorkoutSessionCreate, db: DbSession):
    return crud.create_session(db, data)


@router.get("/{session_id}", response_model=WorkoutSessionRead)
def get_session(session_id: int, db: DbSession):
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(404, "Sesión no encontrada")
    return session


@router.delete("/{session_id}", status_code=204)
def delete_session(session_id: int, db: DbSession):
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(404, "Sesión no encontrada")
    crud.delete_session(db, session)


@router.get("/{session_id}/comparison", response_model=SessionComparison)
def get_comparison(session_id: int, db: DbSession):
    """Compara esta sesión serie a serie con la última sesión anterior del mismo tipo."""
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(404, "Sesión no encontrada")
    previous = crud.get_previous_session(
        db, session.workout_type, session.date, exclude_id=session.id
    )
    return compare_sessions(session, previous)
