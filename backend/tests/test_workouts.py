import datetime


def _session_payload(date: str, weight: float):
    return {
        "date": date,
        "workout_type": "GYM1",
        "exercises": [
            {
                "name": "Sentadilla",
                "order": 1,
                "sets": [
                    {"set_number": 1, "weight_kg": weight, "reps": 9},
                    {"set_number": 2, "weight_kg": weight, "reps": 8},
                ],
            }
        ],
    }


def test_create_session_assigns_cycle_week(client):
    res = client.post("/api/v1/workouts", json=_session_payload("2026-07-13", 80))
    assert res.status_code == 201
    body = res.json()
    assert body["cycle_week"] in (1, 2, 3, 4)
    assert body["exercises"][0]["sets"][0]["weight_kg"] == 80


def test_update_session_replaces_content(client):
    """Autosave del entreno: crear una sesión y luego reemplazar sus series."""
    created = client.post("/api/v1/workouts", json=_session_payload("2026-07-13", 80)).json()
    session_id = created["id"]

    updated = client.put(
        f"/api/v1/workouts/{session_id}",
        json={
            "date": "2026-07-13",
            "workout_type": "GYM1",
            "exercises": [
                {
                    "name": "Sentadilla",
                    "order": 1,
                    "sets": [{"set_number": 1, "weight_kg": 85, "reps": 10}],
                }
            ],
        },
    )
    assert updated.status_code == 200
    body = updated.json()
    # Reemplaza, no acumula: una serie con el nuevo peso
    assert len(body["exercises"][0]["sets"]) == 1
    assert body["exercises"][0]["sets"][0]["weight_kg"] == 85

    # Persistió de verdad (no solo en la respuesta)
    fetched = client.get(f"/api/v1/workouts/{session_id}").json()
    assert fetched["exercises"][0]["sets"][0]["reps"] == 10


def test_running_session_marked_done(client):
    res = client.post(
        "/api/v1/workouts",
        json={"date": "2026-07-14", "workout_type": "RUNNING", "completed": True, "exercises": []},
    )
    assert res.status_code == 201
    assert res.json()["completed"] is True
    assert res.json()["exercises"] == []


def test_session_completed_toggles_via_update(client):
    created = client.post("/api/v1/workouts", json=_session_payload("2026-07-13", 80)).json()
    assert created["completed"] is False  # autosave: en curso

    done = client.put(
        f"/api/v1/workouts/{created['id']}",
        json={
            "date": "2026-07-13",
            "workout_type": "GYM1",
            "completed": True,
            "exercises": created["exercises"]
            and [
                {
                    "name": e["name"],
                    "order": e["order"],
                    "exercise_template_id": e["exercise_template_id"],
                    "sets": [
                        {
                            "set_number": s["set_number"],
                            "weight_kg": s["weight_kg"],
                            "reps": s["reps"],
                        }
                        for s in e["sets"]
                    ],
                }
                for e in created["exercises"]
            ],
        },
    )
    assert done.status_code == 200
    assert done.json()["completed"] is True


def test_update_session_not_found(client):
    assert (
        client.put("/api/v1/workouts/9999", json=_session_payload("2026-07-13", 80)).status_code
        == 404
    )


def test_template_crud(client):
    # CUSTOM no tiene ejercicios sembrados, así que el nuevo va el primero (order 1)
    created = client.post(
        "/api/v1/workouts/templates",
        json={"workout_type": "CUSTOM", "name": "Face pull", "target_sets": 4, "target_reps": "15"},
    )
    assert created.status_code == 201
    tpl_id = created.json()["id"]
    assert created.json()["order"] == 1

    patched = client.patch(
        f"/api/v1/workouts/templates/{tpl_id}", json={"name": "Facepull", "base_weight_kg": 20}
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Facepull"
    assert patched.json()["base_weight_kg"] == 20

    assert client.delete(f"/api/v1/workouts/templates/{tpl_id}").status_code == 204
    custom = client.get("/api/v1/workouts/templates?workout_type=CUSTOM").json()
    assert custom == []


def test_comparison_against_previous_session_of_same_type(client):
    client.post("/api/v1/workouts", json=_session_payload("2026-07-13", 80))
    second = client.post("/api/v1/workouts", json=_session_payload("2026-07-20", 82.5))
    session_id = second.json()["id"]

    comparison = client.get(f"/api/v1/workouts/{session_id}/comparison").json()
    assert comparison["previous_session_id"] is not None
    set_cmp = comparison["exercises"][0]["sets"][0]
    assert set_cmp["weight_delta_kg"] == 2.5
    assert set_cmp["reps_delta"] == 0


def test_comparison_with_no_previous_session_returns_none(client):
    first = client.post("/api/v1/workouts", json=_session_payload("2026-07-13", 80))
    session_id = first.json()["id"]

    comparison = client.get(f"/api/v1/workouts/{session_id}/comparison").json()
    assert comparison["previous_session_id"] is None
    assert comparison["exercises"][0]["sets"][0]["weight_delta_kg"] is None


def test_periodization_endpoint_returns_valid_cycle_week(client):
    res = client.get("/api/v1/workouts/periodization", params={"date": "2026-07-13"})
    assert res.status_code == 200
    body = res.json()
    assert body["cycle_week"] in (1, 2, 3, 4)
    assert "rir_target" in body


def test_running_session_stores_distance_and_shoe(client):
    shoe = client.post("/api/v1/workouts/shoes", json={"name": "Salomon Ultra Glide"}).json()

    res = client.post(
        "/api/v1/workouts",
        json={
            "date": "2026-07-14",
            "workout_type": "RUNNING",
            "completed": True,
            "running_distance_km": 12.5,
            "shoe_id": shoe["id"],
            "exercises": [],
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["running_distance_km"] == 12.5
    assert body["shoe_id"] == shoe["id"]


def test_shoe_crud(client):
    created = client.post("/api/v1/workouts/shoes", json={"name": "Hoka Speedgoat"})
    assert created.status_code == 201
    shoe_id = created.json()["id"]
    assert created.json()["retired"] is False

    listed = client.get("/api/v1/workouts/shoes").json()
    assert any(s["id"] == shoe_id for s in listed)

    retired = client.patch(f"/api/v1/workouts/shoes/{shoe_id}", json={"retired": True})
    assert retired.status_code == 200
    assert retired.json()["retired"] is True

    assert client.delete(f"/api/v1/workouts/shoes/{shoe_id}").status_code == 204
    listed_after = client.get("/api/v1/workouts/shoes").json()
    assert all(s["id"] != shoe_id for s in listed_after)
    assert (
        client.patch(f"/api/v1/workouts/shoes/{shoe_id}", json={"retired": True}).status_code == 404
    )


def test_running_stats_sums_only_completed_running_sessions_in_range(client):
    today = datetime.date.today()
    this_month = today.replace(day=1)
    last_year = today.replace(year=today.year - 1, month=12, day=15)

    # Cuenta: rodaje completado este mes
    client.post(
        "/api/v1/workouts",
        json={
            "date": this_month.isoformat(),
            "workout_type": "RUNNING",
            "completed": True,
            "running_distance_km": 10,
            "exercises": [],
        },
    )
    # No cuenta: rodaje sin terminar (en curso)
    client.post(
        "/api/v1/workouts",
        json={
            "date": this_month.isoformat(),
            "workout_type": "RUNNING",
            "completed": False,
            "running_distance_km": 99,
            "exercises": [],
        },
    )
    # No cuenta: sesión de gym, no de running
    client.post("/api/v1/workouts", json=_session_payload(this_month.isoformat(), 80))
    # No cuenta: año anterior, fuera del rango anual
    client.post(
        "/api/v1/workouts",
        json={
            "date": last_year.isoformat(),
            "workout_type": "RUNNING",
            "completed": True,
            "running_distance_km": 50,
            "exercises": [],
        },
    )

    stats = client.get("/api/v1/workouts/running-stats").json()
    assert stats["km_month"] == 10
    assert stats["km_year"] == 10
