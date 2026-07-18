def test_create_habit_and_reject_duplicate_key(client):
    payload = {
        "key": "mcgill_big3",
        "name": "McGill Big 3",
        "value_type": "boolean",
        "active_days": [0, 2, 4],
    }
    res = client.post("/api/v1/habits", json=payload)
    assert res.status_code == 201

    dup = client.post("/api/v1/habits", json=payload)
    assert dup.status_code == 409


def test_habits_today_reflects_active_days(client):
    client.post(
        "/api/v1/habits",
        json={
            "key": "hip_mobility",
            "name": "Movilidad cadera",
            "value_type": "boolean",
            "active_days": [1, 3],  # Martes y Jueves
        },
    )

    # 2026-07-13 es lunes -> no debido
    monday = client.get("/api/v1/habits/today", params={"date": "2026-07-13"}).json()
    assert monday[0]["due_today"] is False

    # 2026-07-14 es martes -> debido
    tuesday = client.get("/api/v1/habits/today", params={"date": "2026-07-14"}).json()
    assert tuesday[0]["due_today"] is True


def test_streak_breaks_on_missed_due_day(client):
    res = client.post(
        "/api/v1/habits",
        json={
            "key": "mcgill_big3",
            "name": "McGill Big 3",
            "value_type": "boolean",
            "active_days": [0, 2, 4],  # Lun/Mie/Vie
        },
    )
    habit_id = res.json()["id"]

    # Lunes 13, Miercoles 15, Viernes 17 -> todos cumplidos, racha de 3
    for date in ["2026-07-13", "2026-07-15", "2026-07-17"]:
        client.post(f"/api/v1/habits/{habit_id}/logs", json={"date": date, "done": True})

    today = client.get("/api/v1/habits/today", params={"date": "2026-07-17"}).json()
    assert today[0]["current_streak"] == 3

    # Si el miércoles 15 no se cumple, la racha se corta y el viernes solo cuenta 1
    client.post(f"/api/v1/habits/{habit_id}/logs", json={"date": "2026-07-15", "done": False})
    today = client.get("/api/v1/habits/today", params={"date": "2026-07-17"}).json()
    assert today[0]["current_streak"] == 1


def test_update_and_delete_custom_habit(client):
    """Flujo del gestor de hábitos de la UI: crear personalizado, cambiar días, borrar."""
    res = client.post(
        "/api/v1/habits",
        json={
            "key": "1h_de_estudio",
            "name": "1h de estudio",
            "value_type": "numeric",
            "target_value": 60,
            "unit": "min",
            "active_days": [0, 1, 2, 3, 4],
        },
    )
    assert res.status_code == 201
    habit_id = res.json()["id"]

    patched = client.patch(f"/api/v1/habits/{habit_id}", json={"active_days": [5, 6]})
    assert patched.status_code == 200
    assert patched.json()["active_days"] == [5, 6]
    # El resto de campos no enviados no deben cambiar
    assert patched.json()["target_value"] == 60

    deleted = client.delete(f"/api/v1/habits/{habit_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/habits/{habit_id}").status_code == 404


def test_numeric_habit_marks_done_when_target_reached(client):
    res = client.post(
        "/api/v1/habits",
        json={
            "key": "steps",
            "name": "10.000 pasos",
            "value_type": "numeric",
            "target_value": 10000,
            "unit": "pasos",
            "active_days": [0, 1, 2, 3, 4, 5, 6],
        },
    )
    habit_id = res.json()["id"]

    below = client.post(
        f"/api/v1/habits/{habit_id}/logs", json={"date": "2026-07-13", "value": 8000}
    )
    assert below.json()["done"] is False

    above = client.post(
        f"/api/v1/habits/{habit_id}/logs", json={"date": "2026-07-14", "value": 10500}
    )
    assert above.json()["done"] is True
