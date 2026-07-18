import datetime
import enum

from sqlalchemy import JSON, Date, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class HabitValueType(str, enum.Enum):
    BOOLEAN = "boolean"
    NUMERIC = "numeric"


class Habit(Base):
    """Un hábito diario (checklist). `active_days` usa date.weekday(): Lun=0 ... Dom=6.

    Para hábitos numéricos (ej. pasos, agua) `target_value` marca el objetivo y
    `unit` es solo informativo para la UI ("pasos", "L"). Para hábitos booleanos
    (ej. McGill Big 3) `target_value` es None y el log solo guarda `done`.
    """

    __tablename__ = "habits"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(unique=True, index=True)
    name: Mapped[str]
    value_type: Mapped[HabitValueType] = mapped_column(
        Enum(HabitValueType, native_enum=False, length=20), default=HabitValueType.BOOLEAN
    )
    target_value: Mapped[float | None] = mapped_column(default=None)
    unit: Mapped[str | None] = mapped_column(default=None)
    active_days: Mapped[list[int]] = mapped_column(JSON, default=list)
    sort_order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.UTC)
    )

    logs: Mapped[list["HabitLog"]] = relationship(
        back_populates="habit", cascade="all, delete-orphan"
    )

    def is_due_on(self, day: datetime.date) -> bool:
        return day.weekday() in self.active_days


class HabitLog(Base):
    """Registro de cumplimiento de un hábito en una fecha concreta."""

    __tablename__ = "habit_logs"
    __table_args__ = (UniqueConstraint("habit_id", "date", name="uq_habit_log_habit_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    habit_id: Mapped[int] = mapped_column(ForeignKey("habits.id", ondelete="CASCADE"))
    date: Mapped[datetime.date] = mapped_column(Date)
    done: Mapped[bool] = mapped_column(default=False)
    value: Mapped[float | None] = mapped_column(default=None)
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.UTC)
    )

    habit: Mapped["Habit"] = relationship(back_populates="logs")
