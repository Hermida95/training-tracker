import datetime

from pydantic import BaseModel

from app.models.workout import WorkoutType
from app.schemas.workout import PeriodizationInfo


class TodayHabit(BaseModel):
    """Un hábito de la rutina de mañana (los debidos hoy, ver `app/utils/today.py`)."""

    habit_id: int
    name: str
    done: bool


class TodayMeal(BaseModel):
    """El último menú subido. No hay comidas "por día": el menú es un único
    documento (foto/PDF/texto) que el usuario sube y consulta entero."""

    id: int
    title: str
    has_file: bool
    text_excerpt: str | None = None


class TodayTraining(BaseModel):
    workout_type: WorkoutType | None = None
    title: str
    details: str | None = None
    is_rest_day: bool
    source: str | None = None
    periodization: PeriodizationInfo | None = None


class TodaySummary(BaseModel):
    date: datetime.date
    morning_routine: list[TodayHabit]
    meal: TodayMeal | None = None
    training: TodayTraining
