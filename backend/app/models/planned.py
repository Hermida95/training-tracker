import datetime

from sqlalchemy import Date, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.workout import WorkoutType


class PlannedWorkout(Base):
    """Lo que *toca* un día concreto (la prescripción), separado de lo que se
    hace de verdad (WorkoutSession).

    Es la "feature plan por día": un entreno planificado por fecha. Lo genera
    el automatismo de los domingos (source="ai") a partir de las métricas de
    Garmin, pero también puede editarse a mano (source="manual"). Máximo uno
    por usuario y día.

    `workout_type` enlaza con los tipos de la app cuando aplica (Gym A/B/C,
    running); es None para un día de descanso. `title`/`details` son el texto
    que se muestra ("Rodaje fácil 40 min Z2", "Gym A + core", "Descanso").
    """

    __tablename__ = "planned_workouts"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_planned_user_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    date: Mapped[datetime.date] = mapped_column(Date, index=True)
    workout_type: Mapped[WorkoutType | None] = mapped_column(
        Enum(WorkoutType, native_enum=False), default=None
    )
    title: Mapped[str]
    details: Mapped[str | None] = mapped_column(default=None)
    source: Mapped[str] = mapped_column(default="manual")  # "ai" | "manual"
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.UTC)
    )
