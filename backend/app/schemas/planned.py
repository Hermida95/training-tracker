import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.workout import WorkoutType


class PlannedWorkoutIn(BaseModel):
    date: datetime.date
    workout_type: WorkoutType | None = None
    title: str = Field(min_length=1, max_length=120)
    details: str | None = Field(default=None, max_length=2000)
    source: str = "manual"


class PlannedWorkoutRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: datetime.date
    workout_type: WorkoutType | None = None
    title: str
    details: str | None = None
    source: str


class PlannedWorkoutUpdate(BaseModel):
    workout_type: WorkoutType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=120)
    details: str | None = Field(default=None, max_length=2000)


class PlannedMoveIn(BaseModel):
    to_date: datetime.date


class WeekPlanReplace(BaseModel):
    """Reemplaza el plan de una semana completa (lo que usa el automatismo).

    `week_start` es el lunes; se borran los 7 días desde ahí y se insertan los
    `days`. Si un día del rango no viene en `days`, queda sin plan (descanso
    implícito). El origen se marca como "ai" salvo que se diga otra cosa.
    """

    week_start: datetime.date
    days: list[PlannedWorkoutIn]
    source: str = "ai"
