"""Puntuación diaria del checklist y racha de días cumplidos.

Sistema de niveles sobre el % de hábitos debidos completados en el día:
  100%  -> 3 puntos · "perfect" (día perfecto ⭐)
  >=75% -> 2 puntos · "great"
  >=50% -> 1 punto  · "half"
  <50%  -> 0 puntos · "missed"
Un día sin hábitos programados es "rest" y no cuenta ni rompe nada.

La racha cuenta días consecutivos con al menos el 75% (STREAK_THRESHOLD):
un día bueno mantiene la cadena aunque no sea perfecto, que para eso está
el plus de puntos. El día consultado aún sin completar no rompe la racha
(está "pendiente", no "fallado"), igual que en la racha por hábito.

Todo se deriva de habit_logs al vuelo; no se persiste nada.
"""

import datetime

from sqlalchemy.orm import Session

from app.crud import habit as habit_crud
from app.models.habit import Habit, HabitLog
from app.schemas.habit import DayScore

STREAK_THRESHOLD = 0.75
_MAX_LOOKBACK_DAYS = 366


def points_for_rate(rate: float | None) -> tuple[int, str]:
    if rate is None:
        return 0, "rest"
    if rate >= 1.0:
        return 3, "perfect"
    if rate >= 0.75:
        return 2, "great"
    if rate >= 0.5:
        return 1, "half"
    return 0, "missed"


def _logs_by_day(logs: list[HabitLog]) -> dict[datetime.date, dict[int, HabitLog]]:
    result: dict[datetime.date, dict[int, HabitLog]] = {}
    for log in logs:
        result.setdefault(log.date, {})[log.habit_id] = log
    return result


def day_completion(
    habits: list[Habit],
    logs_by_day: dict[datetime.date, dict[int, HabitLog]],
    day: datetime.date,
) -> tuple[int, int, float | None]:
    """(debidos, hechos, ratio) para un día. ratio=None si no hay nada programado."""
    due = [h for h in habits if h.is_due_on(day)]
    if not due:
        return 0, 0, None
    day_logs = logs_by_day.get(day, {})
    done = sum(1 for h in due if (log := day_logs.get(h.id)) and log.done)
    return len(due), done, done / len(due)


def compute_day_score(db: Session, user_id: int, as_of: datetime.date) -> DayScore:
    habits = habit_crud.list_habits(db, user_id)
    start = as_of - datetime.timedelta(days=_MAX_LOOKBACK_DAYS)
    logs_by_day = _logs_by_day(habit_crud.list_all_logs_in_range(db, user_id, start, as_of))

    due, done, rate = day_completion(habits, logs_by_day, as_of)
    points, tier = points_for_rate(rate)

    streak = 0
    day = as_of
    for _ in range(_MAX_LOOKBACK_DAYS):
        _, _, day_rate = day_completion(habits, logs_by_day, day)
        if day_rate is None:
            day -= datetime.timedelta(days=1)
            continue
        if day_rate >= STREAK_THRESHOLD:
            streak += 1
            day -= datetime.timedelta(days=1)
            continue
        if day == as_of:
            # Hoy todavía a medias: no suma pero tampoco rompe.
            day -= datetime.timedelta(days=1)
            continue
        break

    return DayScore(
        date=as_of,
        due_count=due,
        done_count=done,
        completion_rate=round(rate, 3) if rate is not None else None,
        points=points,
        tier=tier,
        streak=streak,
    )
