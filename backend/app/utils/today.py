"""Resumen del día: rutina de mañana + comida + sesión de entreno.

Punto único usado por `GET /api/v1/today`, los crons de recordatorios
(`/internal/notify/*`) y el comando `/hoy` del bot de Telegram, para no
reimplementar tres veces la misma composición de hábitos + menú + plan +
periodización.
"""

import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud import habit as habit_crud
from app.crud import planned as planned_crud
from app.models.menu import MenuDocument
from app.models.workout import WorkoutType
from app.schemas.today import TodayHabit, TodayMeal, TodaySummary, TodayTraining
from app.utils.periodization import compute_cycle_week, get_periodization_info

_MEAL_EXCERPT_CHARS = 300
# La periodización (RIR, +2,5kg S3, descarga S4) solo tiene sentido en las
# sesiones de gimnasio con rutina de series; un rodaje de running o un día
# personalizado no la usan.
_GYM_TYPES = {WorkoutType.GYM1, WorkoutType.GYM2, WorkoutType.GYM3}


def _morning_routine(db: Session, user_id: int, date: datetime.date) -> list[TodayHabit]:
    habits = [h for h in habit_crud.list_habits(db, user_id) if h.is_due_on(date)]
    result = []
    for h in habits:
        log = habit_crud.get_log(db, h.id, date)
        result.append(TodayHabit(habit_id=h.id, name=h.name, done=bool(log and log.done)))
    return result


def _latest_meal(db: Session, user_id: int) -> TodayMeal | None:
    doc = db.scalar(
        select(MenuDocument)
        .where(MenuDocument.user_id == user_id)
        .order_by(MenuDocument.created_at.desc())
    )
    if doc is None:
        return None
    excerpt = None
    if doc.text_content:
        excerpt = doc.text_content[:_MEAL_EXCERPT_CHARS]
        if len(doc.text_content) > _MEAL_EXCERPT_CHARS:
            excerpt += "…"
    return TodayMeal(
        id=doc.id, title=doc.title, has_file=doc.content_type is not None, text_excerpt=excerpt
    )


def _training(db: Session, user_id: int, date: datetime.date) -> TodayTraining:
    planned = planned_crud.get_for_date(db, user_id, date)

    # Sin fila de plan, el hueco es descanso implícito (mismo criterio que
    # `app.crud.planned.move`/`replace_week`: un día sin plan es un día libre).
    if planned is None or planned.workout_type is None:
        return TodayTraining(
            workout_type=None,
            title=planned.title if planned else "Descanso",
            details=planned.details if planned else None,
            is_rest_day=True,
            source=planned.source if planned else None,
        )

    periodization = None
    if planned.workout_type in _GYM_TYPES:
        periodization = get_periodization_info(compute_cycle_week(db, user_id, date))

    return TodayTraining(
        workout_type=planned.workout_type,
        title=planned.title,
        details=planned.details,
        is_rest_day=False,
        source=planned.source,
        periodization=periodization,
    )


def build_today_summary(db: Session, user_id: int, date: datetime.date) -> TodaySummary:
    return TodaySummary(
        date=date,
        morning_routine=_morning_routine(db, user_id, date),
        meal=_latest_meal(db, user_id),
        training=_training(db, user_id, date),
    )
