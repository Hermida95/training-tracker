import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.habit import Habit, HabitLog
from app.schemas.habit import HabitCreate, HabitLogUpsert, HabitUpdate


def list_habits(db: Session) -> list[Habit]:
    return list(db.scalars(select(Habit).order_by(Habit.sort_order, Habit.id)))


def get_habit(db: Session, habit_id: int) -> Habit | None:
    return db.get(Habit, habit_id)


def get_habit_by_key(db: Session, key: str) -> Habit | None:
    return db.scalar(select(Habit).where(Habit.key == key))


def create_habit(db: Session, data: HabitCreate) -> Habit:
    habit = Habit(**data.model_dump())
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


def upsert_log(db: Session, habit_id: int, data: HabitLogUpsert) -> HabitLog:
    log = get_log(db, habit_id, data.date)
    done = data.done
    habit = db.get(Habit, habit_id)
    # Para hábitos numéricos, "done" se infiere de alcanzar el objetivo si no
    # se manda explícitamente (permite que la UI solo mande el valor, ej. pasos).
    if habit and habit.target_value is not None and data.value is not None:
        done = data.value >= habit.target_value

    if log is None:
        log = HabitLog(habit_id=habit_id, date=data.date, done=done, value=data.value)
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


def list_all_logs_in_range(db: Session, start: datetime.date, end: datetime.date) -> list[HabitLog]:
    return list(db.scalars(select(HabitLog).where(HabitLog.date >= start, HabitLog.date <= end)))
