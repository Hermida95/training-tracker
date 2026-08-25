"""Importa todos los modelos para que Alembic (autogenerate) y Base.metadata los vean."""

from app.models.app_setting import AppSetting
from app.models.body_metric import BodyMetric
from app.models.break_event import BreakEvent
from app.models.habit import Habit, HabitLog
from app.models.invite import InviteCode
from app.models.menu import MenuDocument
from app.models.planned import PlannedWorkout
from app.models.user import User
from app.models.workout import (
    ExerciseTemplate,
    Shoe,
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
    "InviteCode",
    "MenuDocument",
    "PlannedWorkout",
    "User",
    "ExerciseTemplate",
    "Shoe",
    "WorkoutExercise",
    "WorkoutSession",
    "WorkoutSet",
]
