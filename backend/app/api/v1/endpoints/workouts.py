import datetime

from fastapi import APIRouter, HTTPException

from app.core.deps import CurrentUser, DbSession
from app.crud import workout as crud
from app.models.workout import WorkoutType
from app.schemas.workout import (
    ExerciseTemplateCreate,
    ExerciseTemplateRead,
    ExerciseTemplateUpdate,
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
def list_templates(db: DbSession, user: CurrentUser, workout_type: WorkoutType | None = None):
    return crud.list_exercise_templates(db, user.id, workout_type)


@router.post("/templates", response_model=ExerciseTemplateRead, status_code=201)
def create_template(data: ExerciseTemplateCreate, db: DbSession, user: CurrentUser):
    """Añade un ejercicio a la rutina del usuario (editor de rutina personal)."""
    return crud.create_template(db, user.id, data)


@router.patch("/templates/{template_id}", response_model=ExerciseTemplateRead)
def update_template(
    template_id: int, data: ExerciseTemplateUpdate, db: DbSession, user: CurrentUser
):
    tpl = crud.get_template(db, user.id, template_id)
    if not tpl:
        raise HTTPException(404, "Ejercicio no encontrado")
    return crud.update_template(db, tpl, data)


@router.delete("/templates/{template_id}", status_code=204)
def delete_template(template_id: int, db: DbSession, user: CurrentUser):
    tpl = crud.get_template(db, user.id, template_id)
    if not tpl:
        raise HTTPException(404, "Ejercicio no encontrado")
    crud.delete_template(db, tpl)


@router.get("/periodization", response_model=PeriodizationInfo)
def periodization(db: DbSession, user: CurrentUser, date: datetime.date | None = None):
    cycle_week = compute_cycle_week(db, user.id, date or today_local())
    return get_periodization_info(cycle_week)


@router.get("", response_model=list[WorkoutSessionRead])
def list_sessions(
    db: DbSession,
    user: CurrentUser,
    workout_type: WorkoutType | None = None,
    start: datetime.date | None = None,
    end: datetime.date | None = None,
    limit: int | None = None,
):
    return crud.list_sessions(db, user.id, workout_type, start, end, limit)


@router.post("", response_model=WorkoutSessionRead, status_code=201)
def create_session(data: WorkoutSessionCreate, db: DbSession, user: CurrentUser):
    return crud.create_session(db, user.id, data)


@router.put("/{session_id}", response_model=WorkoutSessionRead)
def update_session(session_id: int, data: WorkoutSessionCreate, db: DbSession, user: CurrentUser):
    """Reemplaza el contenido de una sesión (autosave del entreno en curso)."""
    session = crud.get_session(db, user.id, session_id)
    if not session:
        raise HTTPException(404, "Sesión no encontrada")
    return crud.update_session(db, session, data)


@router.get("/{session_id}", response_model=WorkoutSessionRead)
def get_session(session_id: int, db: DbSession, user: CurrentUser):
    session = crud.get_session(db, user.id, session_id)
    if not session:
        raise HTTPException(404, "Sesión no encontrada")
    return session


@router.delete("/{session_id}", status_code=204)
def delete_session(session_id: int, db: DbSession, user: CurrentUser):
    session = crud.get_session(db, user.id, session_id)
    if not session:
        raise HTTPException(404, "Sesión no encontrada")
    crud.delete_session(db, session)


@router.get("/{session_id}/comparison", response_model=SessionComparison)
def get_comparison(session_id: int, db: DbSession, user: CurrentUser):
    """Compara esta sesión serie a serie con la última sesión anterior del mismo tipo."""
    session = crud.get_session(db, user.id, session_id)
    if not session:
        raise HTTPException(404, "Sesión no encontrada")
    previous = crud.get_previous_session(
        db, user.id, session.workout_type, session.date, exclude_id=session.id
    )
    return compare_sessions(session, previous)
