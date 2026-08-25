import datetime

from fastapi import APIRouter, HTTPException

from app.core.deps import CurrentUser, DbSession
from app.crud import planned as crud
from app.schemas.planned import (
    PlannedMoveIn,
    PlannedWorkoutIn,
    PlannedWorkoutRead,
    PlannedWorkoutUpdate,
    WeekPlanReplace,
)
from app.utils.timezone import today_local

router = APIRouter(prefix="/planned", tags=["planned"])


@router.get("", response_model=list[PlannedWorkoutRead])
def list_planned(
    db: DbSession,
    user: CurrentUser,
    start: datetime.date | None = None,
    end: datetime.date | None = None,
):
    """Plan de un rango de fechas. Sin parámetros, la semana en curso (Lun-Dom)."""
    if start is None or end is None:
        today = today_local()
        start = today - datetime.timedelta(days=today.weekday())
        end = start + datetime.timedelta(days=6)
    return crud.list_planned(db, user.id, start, end)


@router.get("/today", response_model=PlannedWorkoutRead | None)
def planned_today(db: DbSession, user: CurrentUser, date: datetime.date | None = None):
    """Lo que toca el día indicado (hoy por defecto). None si no hay plan."""
    return crud.get_for_date(db, user.id, date or today_local())


@router.post("", response_model=PlannedWorkoutRead, status_code=201)
def upsert_planned(data: PlannedWorkoutIn, db: DbSession, user: CurrentUser):
    """Crea o reemplaza el plan de un día (uno por día)."""
    return crud.upsert(db, user.id, data)


@router.put("/week", response_model=list[PlannedWorkoutRead])
def replace_week(data: WeekPlanReplace, db: DbSession, user: CurrentUser):
    """Reemplaza el plan de una semana completa (lo usa el cron de los domingos)."""
    return crud.replace_week(db, user.id, data)


@router.patch("/{planned_id}", response_model=PlannedWorkoutRead)
def update_planned(planned_id: int, data: PlannedWorkoutUpdate, db: DbSession, user: CurrentUser):
    planned = crud.get_planned(db, user.id, planned_id)
    if not planned:
        raise HTTPException(404, "Plan no encontrado")
    return crud.update(db, planned, data)


@router.delete("/{planned_id}", status_code=204)
def delete_planned(planned_id: int, db: DbSession, user: CurrentUser):
    planned = crud.get_planned(db, user.id, planned_id)
    if not planned:
        raise HTTPException(404, "Plan no encontrado")
    crud.delete_planned(db, planned)


@router.post("/{planned_id}/move", response_model=list[PlannedWorkoutRead])
def move_planned(planned_id: int, data: PlannedMoveIn, db: DbSession, user: CurrentUser):
    """Mueve un día del plan a otra fecha; si esa fecha ya tiene plan, los intercambia."""
    planned = crud.get_planned(db, user.id, planned_id)
    if not planned:
        raise HTTPException(404, "Plan no encontrado")
    return crud.move(db, planned, data.to_date)
