import datetime

from fastapi import APIRouter, HTTPException

from app.core.deps import CurrentUser, DbSession
from app.crud import habit as crud
from app.schemas.habit import (
    DayScore,
    HabitCreate,
    HabitLogRead,
    HabitLogUpsert,
    HabitRead,
    HabitUpdate,
    HabitWithStatus,
)
from app.utils.day_score import compute_day_score
from app.utils.streak import compute_streak
from app.utils.timezone import today_local

router = APIRouter(prefix="/habits", tags=["habits"])


@router.get("", response_model=list[HabitRead])
def list_habits(db: DbSession, user: CurrentUser):
    return crud.list_habits(db, user.id)


@router.post("", response_model=HabitRead, status_code=201)
def create_habit(data: HabitCreate, db: DbSession, user: CurrentUser):
    if crud.get_habit_by_key(db, user.id, data.key):
        raise HTTPException(409, f"Ya existe un hábito con key '{data.key}'")
    return crud.create_habit(db, user.id, data)


@router.get("/today", response_model=list[HabitWithStatus])
def habits_today(db: DbSession, user: CurrentUser, date: datetime.date | None = None):
    """Checklist del día: para cada hábito, si aplica hoy, si ya se hizo y su racha."""
    target_date = date or today_local()
    result = []
    for h in crud.list_habits(db, user.id):
        log = crud.get_log(db, h.id, target_date)
        result.append(
            HabitWithStatus(
                **HabitRead.model_validate(h).model_dump(),
                due_today=h.is_due_on(target_date),
                done_today=bool(log and log.done),
                value_today=log.value if log else None,
                current_streak=compute_streak(db, h, target_date),
            )
        )
    return result


@router.get("/score", response_model=DayScore)
def day_score(db: DbSession, user: CurrentUser, date: datetime.date | None = None):
    """Puntos del día (100%=3, >=75%=2, >=50%=1) y racha de días >=75%."""
    return compute_day_score(db, user.id, date or today_local())


@router.get("/{habit_id}", response_model=HabitRead)
def get_habit(habit_id: int, db: DbSession, user: CurrentUser):
    habit = crud.get_habit(db, user.id, habit_id)
    if not habit:
        raise HTTPException(404, "Hábito no encontrado")
    return habit


@router.patch("/{habit_id}", response_model=HabitRead)
def update_habit(habit_id: int, data: HabitUpdate, db: DbSession, user: CurrentUser):
    habit = crud.get_habit(db, user.id, habit_id)
    if not habit:
        raise HTTPException(404, "Hábito no encontrado")
    return crud.update_habit(db, habit, data)


@router.delete("/{habit_id}", status_code=204)
def delete_habit(habit_id: int, db: DbSession, user: CurrentUser):
    habit = crud.get_habit(db, user.id, habit_id)
    if not habit:
        raise HTTPException(404, "Hábito no encontrado")
    crud.delete_habit(db, habit)


@router.post("/{habit_id}/logs", response_model=HabitLogRead)
def upsert_log(habit_id: int, data: HabitLogUpsert, db: DbSession, user: CurrentUser):
    habit = crud.get_habit(db, user.id, habit_id)
    if not habit:
        raise HTTPException(404, "Hábito no encontrado")
    return crud.upsert_log(db, habit, data)


@router.get("/{habit_id}/logs", response_model=list[HabitLogRead])
def list_logs(
    habit_id: int, db: DbSession, user: CurrentUser, start: datetime.date, end: datetime.date
):
    if not crud.get_habit(db, user.id, habit_id):
        raise HTTPException(404, "Hábito no encontrado")
    return crud.list_logs_in_range(db, habit_id, start, end)
