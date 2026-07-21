import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.habit import Habit, HabitLog
from app.schemas.habit import HabitCreate, HabitLogUpsert, HabitUpdate


def list_habits(db: Session, user_id: int) -> list[Habit]:
    return list(
        db.scalars(
            select(Habit).where(Habit.user_id == user_id).order_by(Habit.sort_order, Habit.id)
        )
    )


def get_habit(db: Session, user_id: int, habit_id: int) -> Habit | None:
    habit = db.get(Habit, habit_id)
    return habit if habit is not None and habit.user_id == user_id else None


def get_habit_by_key(db: Session, user_id: int, key: str) -> Habit | None:
    return db.scalar(select(Habit).where(Habit.user_id == user_id, Habit.key == key))


def create_habit(db: Session, user_id: int, data: HabitCreate) -> Habit:
    habit = Habit(**data.model_dump(), user_id=user_id)
    db.add(habit)
    db.commit()
    db.refresh(habit)
    return habit


def update_habit(db: Session, habit: Habit, data: HabitUpdate) -> Habit:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(habit, field, value)
    db.commit()
    db.refresh(habit)
    return habit


def delete_habit(db: Session, habit: Habit) -> None:
    db.delete(habit)
    db.commit()


def get_log(db: Session, habit_id: int, date: datetime.date) -> HabitLog | None:
    return db.scalar(select(HabitLog).where(HabitLog.habit_id == habit_id, HabitLog.date == date))


def upsert_log(db: Session, habit: Habit, data: HabitLogUpsert) -> HabitLog:
    log = get_log(db, habit.id, data.date)
    done = data.done
    # Para hábitos numéricos, "done" se infiere de alcanzar el objetivo si no
    # se manda explícitamente (permite que la UI solo mande el valor, ej. pasos).
    if habit.target_value is not None and data.value is not None:
        done = data.value >= habit.target_value

    if log is None:
        log = HabitLog(habit_id=habit.id, date=data.date, done=done, value=data.value)
        db.add(log)
    else:
        log.done = done
        log.value = data.value
    db.commit()
    db.refresh(log)
    return log


def list_logs_in_range(
    db: Session, habit_id: int, start: datetime.date, end: datetime.date
) -> list[HabitLog]:
    return list(
        db.scalars(
            select(HabitLog)
            .where(HabitLog.habit_id == habit_id, HabitLog.date >= start, HabitLog.date <= end)
            .order_by(HabitLog.date)
        )
    )


def list_all_logs_in_range(
    db: Session, user_id: int, start: datetime.date, end: datetime.date
) -> list[HabitLog]:
    """Logs de todos los hábitos del usuario en el rango (join para el scoping)."""
    return list(
        db.scalars(
            select(HabitLog)
            .join(Habit, HabitLog.habit_id == Habit.id)
            .where(Habit.user_id == user_id, HabitLog.date >= start, HabitLog.date <= end)
        )
    )
