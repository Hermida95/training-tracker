import datetime

from pydantic import BaseModel, ConfigDict

from app.models.workout import WorkoutType


class WorkoutSetIn(BaseModel):
    set_number: int
    weight_kg: float | None = None
    reps: int | None = None
    rir: float | None = None


class WorkoutSetRead(WorkoutSetIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


class WorkoutExerciseIn(BaseModel):
    name: str
    order: int = 0
    exercise_template_id: int | None = None
    sets: list[WorkoutSetIn] = []


class WorkoutExerciseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    order: int
    exercise_template_id: int | None = None
    sets: list[WorkoutSetRead] = []


class WorkoutSessionCreate(BaseModel):
    date: datetime.date
    workout_type: WorkoutType
    notes: str | None = None
    running_minutes: int | None = None
    running_feeling: int | None = None
    exercises: list[WorkoutExerciseIn] = []


class WorkoutSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: datetime.date
    workout_type: WorkoutType
    cycle_week: int
    notes: str | None = None
    running_minutes: int | None = None
    running_feeling: int | None = None
    exercises: list[WorkoutExerciseRead] = []


class ExerciseTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workout_type: WorkoutType
    name: str
    order: int
    target_sets: int
    target_reps: str
    base_weight_kg: float | None = None


class SetComparison(BaseModel):
    set_number: int
    previous_weight_kg: float | None = None
    previous_reps: int | None = None
    current_weight_kg: float | None = None
    current_reps: int | None = None
    weight_delta_kg: float | None = None
    reps_delta: int | None = None


class ExerciseComparison(BaseModel):
    name: str
    sets: list[SetComparison]


class SessionComparison(BaseModel):
    """Comparación de una sesión contra la última sesión anterior del mismo tipo."""

    current_session_id: int
    previous_session_id: int | None
    previous_date: datetime.date | None
    exercises: list[ExerciseComparison]


class PeriodizationInfo(BaseModel):
    cycle_week: int
    label: str
    rir_target: str
    weight_adjustment_kg: float
    set_adjustment: int
    description: str
