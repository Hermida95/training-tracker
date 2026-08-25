from sqlalchemy import select

from app.models.user import User
from app.seed.hybrid_plan import apply_to_user
from tests.conftest import register_user


def test_hybrid_plan_replaces_gym_and_extends_mcgill(anon_client, db_session):
    # Usuario con los datos por defecto sembrados (register_user no los borra).
    headers = register_user(anon_client, "atleta@example.com")
    user = db_session.scalar(select(User).where(User.email == "atleta@example.com"))

    apply_to_user(db_session, user.id)

    # Gym A/B/C: 6 + 6 + 7 = 19 ejercicios
    gym = anon_client.get("/api/v1/workouts/templates", headers=headers).json()
    gym_only = [t for t in gym if t["workout_type"].startswith("GYM")]
    assert len(gym_only) == 19
    names = {t["name"] for t in gym_only}
    assert {"Sentadilla con barra", "Peso muerto rumano", "Pallof press"} <= names
    assert "Prensa de piernas ligera" in names  # el viernes ya no lleva pierna pesada

    # McGill Big 3 pasa a incluir los días de carrera (Mar/Jue/Sáb = 1,3,5)
    habits = anon_client.get("/api/v1/habits", headers=headers).json()
    mcgill = next(h for h in habits if h["key"] == "mcgill_big3")
    assert set(mcgill["active_days"]) >= {1, 3, 5}


def test_hybrid_plan_is_idempotent(anon_client, db_session):
    headers = register_user(anon_client, "atleta2@example.com")
    user = db_session.scalar(select(User).where(User.email == "atleta2@example.com"))

    apply_to_user(db_session, user.id)
    apply_to_user(db_session, user.id)  # segunda pasada: no debe duplicar

    gym = [
        t
        for t in anon_client.get("/api/v1/workouts/templates", headers=headers).json()
        if t["workout_type"].startswith("GYM")
    ]
    assert len(gym) == 19
