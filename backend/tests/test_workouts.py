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
