import datetime

from pydantic import BaseModel


class MonthlyStats(BaseModel):
    year: int
    month: int
    sessions_completed: int
    sessions_by_type: dict[str, int]
    avg_steps: float | None
    steps_goal_days: int
    weight_start_kg: float | None
    weight_end_kg: float | None
    weight_trend_kg: float | None
    waist_start_cm: float | None
    waist_end_cm: float | None
    waist_trend_cm: float | None
    breaks_done: int
    breaks_total: int
    habit_completion_rate: float
    points_total: int
    perfect_days: int


class ExportPayload(BaseModel):
    generated_at: datetime.datetime
    stats: MonthlyStats
    workouts: list[dict]
    habits: list[dict]
    body_metrics: list[dict]
