"""Plan híbrido Fuerza + Trail/Ultra — Bloque 1 (fase de base).

Aplica a UNA cuenta concreta (no cambia el seed por defecto de nuevos usuarios):
reemplaza sus rutinas de gimnasio por Gym A/B/C y añade McGill Big 3 en los
días de carrera. Se ejecuta a mano contra la BD del usuario:

    python -m app.seed.hybrid_plan miguel@example.com          # local
    DATABASE_URL=<neon> python -m app.seed.hybrid_plan <email> # producción

Es idempotente: borra las plantillas de gym existentes de la cuenta y las
recrea, así que volver a ejecutarlo deja el mismo resultado.
"""

import sys

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.habit import Habit
from app.models.user import User
from app.models.workout import ExerciseTemplate, WorkoutType
from app.utils.seed_keys import MCGILL_KEY

# weekday: Lunes=0 ... Domingo=6. Días de carrera del plan: martes, jueves, sábado.
RUNNING_DAYS = [1, 3, 5]

# (tipo, orden, nombre, series, reps, peso_base_kg)
GYM_A = [  # Lunes · Fuerza tren inferior + Empuje
    (1, "Sentadilla con barra", 4, "6-8", 80),
    (2, "Press de banca", 3, "8-10", 70),
    (3, "Leg extension", 3, "12-15", 78),
    (4, "Jalón al pecho", 3, "10-12", 59),
    (5, "Elevación de gemelo de pie", 3, "15-20", None),
    (6, "Tríceps polea (cuerda)", 3, "12-15", 20),
]
GYM_B = [  # Miércoles · Cadena posterior + Tracción
    (1, "Peso muerto rumano", 4, "8-10", 70),
    (2, "Hip thrust", 3, "10-12", 100),
    (3, "Remo sentado", 3, "10-12", 52),
    (4, "Zancadas con mancuernas", 3, "10/pierna", 20),
    (5, "Press militar mancuernas", 3, "8-10", 15),
    (6, "Bíceps en polea", 3, "12", 41),
]
GYM_C = [  # Viernes · Empuje/Hombro + Core (piernas descargadas para el sábado)
    (1, "Press inclinado mancuernas", 4, "8-12", 55),
    (2, "Dominadas o jalón supino", 3, "8-12", None),
    (3, "Facepulls", 3, "15-20", 15),
    (4, "Elevaciones laterales", 3, "12-15", 7),
    (5, "Prensa de piernas ligera", 2, "15", 50),
    (6, "Pallof press", 3, "12/lado", None),
    (7, "Plancha lateral", 3, "30-45s", None),
]

_DAYS = {WorkoutType.GYM1: GYM_A, WorkoutType.GYM2: GYM_B, WorkoutType.GYM3: GYM_C}


def apply_to_user(db: Session, user_id: int) -> None:
    # 1) Rutinas de gimnasio: borra las de gym y recrea A/B/C.
    db.execute(
        delete(ExerciseTemplate).where(
            ExerciseTemplate.user_id == user_id,
            ExerciseTemplate.workout_type.in_(
                [WorkoutType.GYM1, WorkoutType.GYM2, WorkoutType.GYM3]
            ),
        )
    )
    for workout_type, rows in _DAYS.items():
        for order, name, sets, reps, weight in rows:
            db.add(
                ExerciseTemplate(
                    user_id=user_id,
                    workout_type=workout_type,
                    order=order,
                    name=name,
                    target_sets=sets,
                    target_reps=reps,
                    base_weight_kg=weight,
                )
            )

    # 2) McGill Big 3 también los días de carrera (además de los que ya tuviera).
    mcgill = db.scalar(select(Habit).where(Habit.user_id == user_id, Habit.key == MCGILL_KEY))
    if mcgill is not None:
        merged = sorted(set(mcgill.active_days) | set(RUNNING_DAYS))
        mcgill.active_days = merged

    db.commit()


def main() -> None:
    if len(sys.argv) != 2:
        print("Uso: python -m app.seed.hybrid_plan <email>")
        raise SystemExit(1)
    email = sys.argv[1].lower()
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            print(f"No existe ninguna cuenta con el email {email}")
            raise SystemExit(1)
        apply_to_user(db, user.id)
        gym = db.scalars(select(ExerciseTemplate).where(ExerciseTemplate.user_id == user.id)).all()
        mcgill = db.scalar(select(Habit).where(Habit.user_id == user.id, Habit.key == MCGILL_KEY))
        gym_count = len([t for t in gym if t.workout_type.value.startswith("GYM")])
        print(f"Plan híbrido aplicado a {email} (id={user.id})")
        print(f"  Ejercicios de gimnasio: {gym_count}")
        if mcgill:
            print(f"  McGill Big 3 activo los días (0=Lun): {mcgill.active_days}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
