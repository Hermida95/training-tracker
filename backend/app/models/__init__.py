"""Importa todos los modelos para que Alembic (autogenerate) y Base.metadata los vean."""

from app.models.app_setting import AppSetting
from app.models.body_metric import BodyMetric
from app.models.break_event import BreakEvent
from app.models.habit import Habit, HabitLog
from app.models.workout import (
    ExerciseTemplate,
    WorkoutExercise,
    WorkoutSession,
    WorkoutSet,
)

__all__ = [
    "AppSetting",
    "BodyMetric",
    "BreakEvent",
    "Habit",
    "HabitLog",
    "ExerciseTemplate",
    "WorkoutExercise",
    "WorkoutSession",
    "WorkoutSet",
]
