import calendar
import datetime

from sqlalchemy.orm import Session

from app.crud import body_metric as body_metric_crud
from app.crud import break_event as break_crud
from app.crud import habit as habit_crud
from app.crud import workout as workout_crud
from app.models.break_event import BreakStatus
from app.models.habit import HabitLog
from app.schemas.stats import MonthlyStats
from app.utils.day_score import day_completion, points_for_rate
from app.utils.seed_keys import STEPS_KEY


def month_bounds(year: int, month: int) -> tuple[datetime.date, datetime.date]:
    last_day = calendar.monthrange(year, month)[1]
    return datetime.date(year, month, 1), datetime.date(year, month, last_day)


def compute_monthly_stats(db: Session, year: int, month: int) -> MonthlyStats:
    start, end = month_bounds(year, month)

    sessions = workout_crud.list_sessions(db, start=start, end=end)
    sessions_by_type: dict[str, int] = {}
    for s in sessions:
        sessions_by_type[s.workout_type.value] = sessions_by_type.get(s.workout_type.value, 0) + 1

    steps_habit = habit_crud.get_habit_by_key(db, STEPS_KEY)
    avg_steps = None
    steps_goal_days = 0
    if steps_habit:
        logs = habit_crud.list_logs_in_range(db, steps_habit.id, start, end)
        values = [log.value for log in logs if log.value is not None]
        if values:
            avg_steps = round(sum(values) / len(values), 0)
        steps_goal_days = sum(1 for log in logs if log.done)

    metrics = body_metric_crud.list_metrics(db, start, end)
    weights = [m for m in metrics if m.weight_kg is not None]
    waists = [m for m in metrics if m.waist_cm is not None]
    weight_start = weights[0].weight_kg if weights else None
    weight_end = weights[-1].weight_kg if weights else None
    waist_start = waists[0].waist_cm if waists else None
    waist_end = waists[-1].waist_cm if waists else None

    breaks = break_crud.list_breaks(
        db,
        start=datetime.datetime.combine(start, datetime.time.min),
        end=datetime.datetime.combine(end, datetime.time.max),
    )
    breaks_done = sum(1 for b in breaks if b.status == BreakStatus.DONE)

    all_habits = habit_crud.list_habits(db)
    all_logs = habit_crud.list_all_logs_in_range(db, start, end)
    logs_by_day: dict[datetime.date, dict[int, HabitLog]] = {}
    for log in all_logs:
        logs_by_day.setdefault(log.date, {})[log.habit_id] = log

    due_count = 0
    done_count = 0
    points_total = 0
    perfect_days = 0
    day = start
    while day <= end:
        day_due, day_done, day_rate = day_completion(all_habits, logs_by_day, day)
        due_count += day_due
        done_count += day_done
        points, tier = points_for_rate(day_rate)
        points_total += points
        if tier == "perfect":
            perfect_days += 1
        day += datetime.timedelta(days=1)

    return MonthlyStats(
        year=year,
        month=month,
        sessions_completed=len(sessions),
        sessions_by_type=sessions_by_type,
        avg_steps=avg_steps,
        steps_goal_days=steps_goal_days,
        weight_start_kg=weight_start,
        weight_end_kg=weight_end,
        weight_trend_kg=round(weight_end - weight_start, 2)
        if weight_start is not None and weight_end is not None
        else None,
        waist_start_cm=waist_start,
        waist_end_cm=waist_end,
        waist_trend_cm=round(waist_end - waist_start, 2)
        if waist_start is not None and waist_end is not None
        else None,
        breaks_done=breaks_done,
        breaks_total=len(breaks),
        habit_completion_rate=round(done_count / due_count, 3) if due_count else 0.0,
        points_total=points_total,
        perfect_days=perfect_days,
    )
