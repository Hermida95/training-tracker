def test_break_config_defaults(client):
    res = client.get("/api/v1/breaks/config")
    assert res.status_code == 200
    body = res.json()
    assert body["interval_minutes"] == 45
    assert body["window_start"] == "08:30"
    assert body["window_end"] == "15:00"
    assert body["timezone"] == "Europe/Madrid"


def test_update_break_config_persists(client):
    client.put(
        "/api/v1/breaks/config",
        json={
            "interval_minutes": 50,
            "window_start": "09:00",
            "window_end": "14:00",
            "timezone": "Europe/Madrid",
        },
    )
    res = client.get("/api/v1/breaks/config")
    assert res.json()["interval_minutes"] == 50
    assert res.json()["window_start"] == "09:00"


def test_mark_done_and_postpone(client):
    created = client.post("/api/v1/breaks", json={"scheduled_for": "2026-07-17T09:15:00"}).json()

    done = client.post(f"/api/v1/breaks/{created['id']}/done").json()
    assert done["status"] == "done"
    assert done["responded_at"] is not None

    created2 = client.post("/api/v1/breaks", json={"scheduled_for": "2026-07-17T10:00:00"}).json()
    postponed = client.post(f"/api/v1/breaks/{created2['id']}/postpone?minutes=5").json()
    assert postponed["scheduled_for"] == "2026-07-17T10:05:00"
    assert postponed["postponed_from_id"] == created2["id"]

    original_after = client.get("/api/v1/breaks").json()
    original = next(b for b in original_after if b["id"] == created2["id"])
    assert original["status"] == "postponed"
