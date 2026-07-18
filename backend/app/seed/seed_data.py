"""Siembra la BD con la rutina precargada y los hábitos diarios del spec.

Idempotente: se puede ejecutar en cada arranque del contenedor (ver
docker-compose.yml) sin duplicar filas, comprobando primero si ya existen.

Uso: python -m app.seed.seed_data
"""

from app.core.database import Base, SessionLocal, engine
from app.models.habit import Habit, HabitValueType
from app.models.workout import ExerciseTemplate, WorkoutType
from app.utils.seed_keys import (
    HIP_MOBILITY_KEY,
    MCGILL_KEY,
    STEPS_KEY,
    SUNDAY_WALK_KEY,
    WATER_KEY,
)

# weekday: Lunes=0 ... Domingo=6
HABITS = [
    dict(
        key=MCGILL_KEY,
        name="McGill Big 3 (8 min)",
        value_type=HabitValueType.BOOLEAN,
        active_days=[0, 2, 4],
        sort_order=1,
    ),
    dict(
        key=HIP_MOBILITY_KEY,
        name="Movilidad de cadera (10 min)",
        value_type=HabitValueType.BOOLEAN,
        active_days=[1, 3],
        sort_order=2,
    ),
    dict(
        key=SUNDAY_WALK_KEY,
        name="Paseo de descanso",
        value_type=HabitValueType.BOOLEAN,
        active_days=[6],
        sort_order=3,
    ),
    dict(
        key=STEPS_KEY,
        name="10.000 pasos",
        value_type=HabitValueType.NUMERIC,
        target_value=10000,
        unit="pasos",
        active_days=[0, 1, 2, 3, 4, 5, 6],
        sort_order=4,
    ),
    dict(
        key=WATER_KEY,
        name="2L de agua",
        value_type=HabitValueType.NUMERIC,
        target_value=2,
        unit="L",
        active_days=[0, 1, 2, 3, 4, 5, 6],
        sort_order=5,
    ),
]

# GYM1 (Lunes), GYM2 (Miércoles), GYM3 (Viernes): peso base = semana 1 (RIR 3).
# Tupla: (tipo, orden, nombre, target_sets, target_reps, base_weight_kg)
_EXERCISE_ROWS: list[tuple[WorkoutType, int, str, int, str, float | None]] = [
    # --- GYM1 · Lunes ---
    (WorkoutType.GYM1, 1, "Sentadilla", 3, "8-10", 80),
    (WorkoutType.GYM1, 2, "Press banca", 3, "8-10", 70),
    (WorkoutType.GYM1, 3, "Jalón", 3, "10-12", 59),
    (WorkoutType.GYM1, 4, "Leg extension", 3, "12-15", 78),
    (WorkoutType.GYM1, 5, "Tríceps cuerda", 3, "12", 20),
    (WorkoutType.GYM1, 6, "Dead bug", 3, "10/lado", None),
    # --- GYM2 · Miércoles ---
    (WorkoutType.GYM2, 1, "Peso muerto rumano", 3, "10-12", 60),
    (WorkoutType.GYM2, 2, "Remo sentado", 3, "10-12", 52),
    (WorkoutType.GYM2, 3, "Zancadas", 3, "10/pierna", 20),
    (WorkoutType.GYM2, 4, "Press militar", 3, "8-10", 30),
    (WorkoutType.GYM2, 5, "Bíceps polea", 3, "12", 41),
    (WorkoutType.GYM2, 6, "Pallof", 3, "12/lado", None),
    # --- GYM3 · Viernes ---
    (WorkoutType.GYM3, 1, "Hip thrust", 3, "10-12", 100),
    (WorkoutType.GYM3, 2, "Prensa", 3, "12-15", 75),
    (WorkoutType.GYM3, 3, "Press inclinado", 3, "10-12", 55),
    (WorkoutType.GYM3, 4, "Facepulls", 3, "15", 15),
    (WorkoutType.GYM3, 5, "Elevaciones laterales", 3, "12", 14),
    (WorkoutType.GYM3, 6, "Plancha con disco", 3, "30-40s", None),
]

EXERCISE_TEMPLATES = [
    dict(
        workout_type=workout_type,
        order=order,
        name=name,
        target_sets=target_sets,
        target_reps=target_reps,
        base_weight_kg=base_weight_kg,
    )
    for workout_type, order, name, target_sets, target_reps, base_weight_kg in _EXERCISE_ROWS
]


def seed(db) -> None:
    if db.query(Habit).count() == 0:
        for h in HABITS:
            db.add(Habit(**h))
        print(f"Seed: {len(HABITS)} hábitos creados")

    if db.query(ExerciseTemplate).count() == 0:
        for t in EXERCISE_TEMPLATES:
            db.add(ExerciseTemplate(**t))
        print(f"Seed: {len(EXERCISE_TEMPLATES)} ejercicios de plantilla creados")

    db.commit()


def main() -> None:
    Base.metadata.create_all(bind=engine)  # no-op si Alembic ya corrió las migraciones
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
