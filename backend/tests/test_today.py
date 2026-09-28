# 2026-08-24 es lunes (mismo ancla de fecha que tests/test_planned.py).
MONDAY = "2026-08-24"
TUESDAY = "2026-08-25"


def test_today_defaults_to_rest_day_without_a_plan(client):
    today = client.get("/api/v1/today", params={"date": MONDAY}).json()
    assert today["training"] == {
        "workout_type": None,
        "title": "Descanso",
        "details": None,
        "is_rest_day": True,
        "source": None,
        "periodization": None,
    }


def test_today_includes_periodization_for_a_planned_gym_session(client):
    client.post(
        "/api/v1/planned",
        json={
            "date": MONDAY,
            "workout_type": "GYM1",
            "title": "Gym A",
            "details": "Sentadilla 4x8",
        },
    )
    today = client.get("/api/v1/today", params={"date": MONDAY}).json()
    training = today["training"]
    assert training["is_rest_day"] is False
    assert training["workout_type"] == "GYM1"
    assert training["title"] == "Gym A"
    # program_start_date se siembra con la fecha real de "hoy" en el primer
    # acceso (ver app/utils/app_settings.py): no hay una semana de ciclo fija
    # para una fecha ancla arbitraria, igual que test_workouts.py.
    assert training["periodization"]["cycle_week"] in (1, 2, 3, 4)
    assert "rir_target" in training["periodization"]


def test_today_skips_periodization_for_a_running_session(client):
    client.post(
        "/api/v1/planned",
        json={"date": MONDAY, "workout_type": "RUNNING", "title": "Rodaje 40 min Z2"},
    )
    today = client.get("/api/v1/today", params={"date": MONDAY}).json()
    assert today["training"]["periodization"] is None


def test_today_morning_routine_reflects_due_days_and_done_status(client):
    habit = client.post(
        "/api/v1/habits",
        json={
            "key": "estiramientos",
            "name": "Estiramientos",
            "value_type": "boolean",
            "active_days": [0],  # solo lunes
        },
    ).json()

    monday = client.get("/api/v1/today", params={"date": MONDAY}).json()
    assert monday["morning_routine"] == [
        {"habit_id": habit["id"], "name": "Estiramientos", "done": False}
    ]

    client.post(f"/api/v1/habits/{habit['id']}/logs", json={"date": MONDAY, "done": True})
    monday_done = client.get("/api/v1/today", params={"date": MONDAY}).json()
    assert monday_done["morning_routine"][0]["done"] is True

    tuesday = client.get("/api/v1/today", params={"date": TUESDAY}).json()
    assert tuesday["morning_routine"] == []


def test_today_meal_is_the_latest_uploaded_menu(client):
    assert client.get("/api/v1/today", params={"date": MONDAY}).json()["meal"] is None

    client.post(
        "/api/v1/menu", data={"title": "Semana 1", "text_content": "Lunes: pollo con arroz"}
    )
    second = client.post(
        "/api/v1/menu", data={"title": "Semana 2", "text_content": "Lunes: salmón"}
    ).json()

    meal = client.get("/api/v1/today", params={"date": MONDAY}).json()["meal"]
    assert meal["id"] == second["id"]
    assert meal["title"] == "Semana 2"
    assert meal["has_file"] is False
    assert meal["text_excerpt"] == "Lunes: salmón"


def test_today_requires_auth(anon_client):
    assert anon_client.get("/api/v1/today").status_code == 401


def test_today_is_private_per_user(client, anon_client):
    from tests.conftest import register_user

    client.post(
        "/api/v1/planned", json={"date": MONDAY, "workout_type": "GYM1", "title": "Mi sesión"}
    )
    headers_b = register_user(anon_client, "otro@example.com", invited_by=client.headers)
    today_b = anon_client.get("/api/v1/today", params={"date": MONDAY}, headers=headers_b).json()
    assert today_b["training"]["is_rest_day"] is True
