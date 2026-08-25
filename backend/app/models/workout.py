import datetime
import enum

from sqlalchemy import Date, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class WorkoutType(str, enum.Enum):
    GYM1 = "GYM1"  # Lunes: sentadilla, press banca, jalón...
    GYM2 = "GYM2"  # Miércoles: peso muerto rumano, remo...
    GYM3 = "GYM3"  # Viernes: hip thrust, prensa...
    RUNNING = "RUNNING"  # Sábado: Z2
    CUSTOM = "CUSTOM"


class ExerciseTemplate(Base):
    """Rutina precargada: qué ejercicios componen cada tipo de sesión y su objetivo base.

    `base_weight_kg` es el peso de referencia de la semana 1 (RIR 3). La progresión
    de semanas 2-4 la calcula `app.utils.periodization` a partir de este valor,
    no se persiste una copia por semana.
    """

    __tablename__ = "exercise_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    workout_type: Mapped[WorkoutType] = mapped_column(Enum(WorkoutType, native_enum=False))
    name: Mapped[str]
    order: Mapped[int] = mapped_column(default=0)
    target_sets: Mapped[int] = mapped_column(default=3)
    target_reps: Mapped[str] = mapped_column(default="")  # ej. "8-10", "30-40s"
    base_weight_kg: Mapped[float | None] = mapped_column(default=None)


class WorkoutSession(Base):
    """Una sesión de entreno concreta (una fecha + un tipo)."""

    __tablename__ = "workout_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    date: Mapped[datetime.date] = mapped_column(Date, index=True)
    workout_type: Mapped[WorkoutType] = mapped_column(Enum(WorkoutType, native_enum=False))
    cycle_week: Mapped[int] = mapped_column(default=1)  # 1-4, ver app.utils.periodization
    # False = en curso (autosave a medias); True = el usuario la dio por terminada.
    # Un rodaje marcado "hecho" nace ya con completed=True (no se registra nada más).
    completed: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[str | None] = mapped_column(default=None)
    running_minutes: Mapped[int | None] = mapped_column(default=None)
    running_feeling: Mapped[int | None] = mapped_column(default=None)  # 1-5
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.UTC)
    )

    exercises: Mapped[list["WorkoutExercise"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="WorkoutExercise.order"
    )


class WorkoutExercise(Base):
    """Un ejercicio dentro de una sesión. `name` es una copia (snapshot) del template
    para que si el usuario edita la rutina más adelante, el histórico no cambie."""

    __tablename__ = "workout_exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("workout_sessions.id", ondelete="CASCADE"))
    exercise_template_id: Mapped[int | None] = mapped_column(
        ForeignKey("exercise_templates.id", ondelete="SET NULL"), default=None
    )
    name: Mapped[str]
    order: Mapped[int] = mapped_column(default=0)

    session: Mapped["WorkoutSession"] = relationship(back_populates="exercises")
    sets: Mapped[list["WorkoutSet"]] = relationship(
        back_populates="exercise", cascade="all, delete-orphan", order_by="WorkoutSet.set_number"
    )


class WorkoutSet(Base):
    """Una serie: peso x reps (+ RIR opcional). El registro debe poder hacerse
    en 2 toques desde la UI: tocar peso (+/-) y tocar reps (+/-), o pegar el
    valor del template con un solo tap."""

    __tablename__ = "workout_sets"

    id: Mapped[int] = mapped_column(primary_key=True)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("workout_exercises.id", ondelete="CASCADE"))
    set_number: Mapped[int]
    weight_kg: Mapped[float | None] = mapped_column(default=None)
    reps: Mapped[int | None] = mapped_column(default=None)
    rir: Mapped[float | None] = mapped_column(default=None)

    exercise: Mapped["WorkoutExercise"] = relationship(back_populates="sets")
