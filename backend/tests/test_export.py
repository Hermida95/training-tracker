def test_export_json_contains_stats_and_workouts(client):
    client.post(
        "/api/v1/workouts",
        json={"date": "2026-07-13", "workout_type": "GYM1", "exercises": []},
    )
    res = client.get("/api/v1/export", params={"year": 2026, "month": 7, "format": "json"})
    assert res.status_code == 200
    body = res.json()
    assert body["stats"]["sessions_completed"] == 1
    assert len(body["workouts"]) == 1


def test_export_text_is_plain_text_and_mentions_month(client):
    res = client.get("/api/v1/export", params={"year": 2026, "month": 7, "format": "text"})
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/plain")
    assert "RESUMEN 07/2026" in res.text
