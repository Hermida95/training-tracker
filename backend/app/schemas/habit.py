import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.habit import HabitValueType


class HabitBase(BaseModel):
    key: str
    name: str
    value_type: HabitValueType = HabitValueType.BOOLEAN
    target_value: float | None = None
    unit: str | None = None
    active_days: list[int] = Field(default_factory=list, description="0=Lunes ... 6=Domingo")
    sort_order: int = 0


class HabitCreate(HabitBase):
    pass


class HabitUpdate(BaseModel):
    name: str | None = None
    target_value: float | None = None
    unit: str | None = None
    active_days: list[int] | None = None
    sort_order: int | None = None


class HabitRead(HabitBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime.datetime


class HabitWithStatus(HabitRead):
    """Hábito + su estado calculado para el día consultado (usado en /habits/today)."""

    due_today: bool
    done_today: bool
    value_today: float | None = None
    current_streak: int


class DayScore(BaseModel):
    """Puntuación del checklist de un día + racha de días >=75%.

    tier: "perfect" (100%, 3pts) | "great" (>=75%, 2pts) | "half" (>=50%, 1pt)
          | "missed" (<50%, 0pts) | "rest" (nada programado).
    """

    date: datetime.date
    due_count: int
    done_count: int
    completion_rate: float | None
    points: int
    tier: str
    streak: int


class HabitLogUpsert(BaseModel):
    date: datetime.date
    done: bool = False
    value: float | None = None


class HabitLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    habit_id: int
    date: datetime.date
    done: bool
    value: float | None = None
