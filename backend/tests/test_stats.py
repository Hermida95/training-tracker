def test_monthly_stats_aggregates_sessions_and_weight_trend(client):
    client.post(
        "/api/v1/workouts",
        json={"date": "2026-07-06", "workout_type": "GYM1", "exercises": []},
    )
    client.post(
        "/api/v1/workouts",
        json={"date": "2026-07-13", "workout_type": "GYM1", "exercises": []},
    )
    client.post("/api/v1/body-metrics", json={"date": "2026-07-06", "weight_kg": 82.0})
    client.post("/api/v1/body-metrics", json={"date": "2026-07-27", "weight_kg": 80.0})

    res = client.get("/api/v1/stats/monthly", params={"year": 2026, "month": 7})
    body = res.json()
    assert body["sessions_completed"] == 2
    assert body["sessions_by_type"]["GYM1"] == 2
    assert body["weight_trend_kg"] == -2.0


def test_monthly_stats_empty_month_does_not_error(client):
    res = client.get("/api/v1/stats/monthly", params={"year": 2026, "month": 1})
    assert res.status_code == 200
    body = res.json()
    assert body["sessions_completed"] == 0
    assert body["habit_completion_rate"] == 0.0
