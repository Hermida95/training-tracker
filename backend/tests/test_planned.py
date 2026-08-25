def test_upsert_and_get_today(client):
    res = client.post(
        "/api/v1/planned",
        json={
            "date": "2026-08-24",
            "workout_type": "GYM1",
            "title": "Gym A + core",
            "details": "Sentadilla 4x6-8 @80",
        },
    )
    assert res.status_code == 201

    # Upsert: mismo día reemplaza, no duplica
    res2 = client.post(
        "/api/v1/planned",
        json={"date": "2026-08-24", "title": "Descanso"},
    )
    assert res2.status_code == 201

    got = client.get("/api/v1/planned/today", params={"date": "2026-08-24"}).json()
    assert got["title"] == "Descanso"
    assert got["workout_type"] is None


def test_replace_week(client):
    payload = {
        "week_start": "2026-08-24",  # lunes
        "source": "ai",
        "days": [
            {"date": "2026-08-24", "workout_type": "GYM1", "title": "Gym A"},
            {"date": "2026-08-25", "workout_type": "RUNNING", "title": "Rodaje 35 min Z2"},
            {"date": "2026-08-30", "title": "Descanso"},
        ],
    }
    res = client.put("/api/v1/planned/week", json=payload)
    assert res.status_code == 200
    assert len(res.json()) == 3
    assert all(d["source"] == "ai" for d in res.json())

    week = client.get("/api/v1/planned", params={"start": "2026-08-24", "end": "2026-08-30"}).json()
    assert [d["date"] for d in week] == ["2026-08-24", "2026-08-25", "2026-08-30"]

    # Reemplazar de nuevo no acumula
    res2 = client.put(
        "/api/v1/planned/week",
        json={"week_start": "2026-08-24", "days": [{"date": "2026-08-24", "title": "Solo lunes"}]},
    )
    assert len(res2.json()) == 1
    week = client.get("/api/v1/planned", params={"start": "2026-08-24", "end": "2026-08-30"}).json()
    assert len(week) == 1


def test_manual_edit_marks_source_manual(client):
    created = client.post(
        "/api/v1/planned", json={"date": "2026-08-24", "title": "Gym A", "source": "ai"}
    ).json()
    patched = client.patch(
        f"/api/v1/planned/{created['id']}", json={"title": "Gym A (movido)"}
    ).json()
    assert patched["title"] == "Gym A (movido)"
    assert patched["source"] == "manual"


def test_planned_is_private_per_user(client, anon_client):
    from tests.conftest import register_user

    mine = client.post("/api/v1/planned", json={"date": "2026-08-24", "title": "Mío"}).json()
    headers_b = register_user(anon_client, "otro@example.com", invited_by=client.headers)
    assert (
        anon_client.get(
            "/api/v1/planned",
            params={"start": "2026-08-24", "end": "2026-08-24"},
            headers=headers_b,
        ).json()
        == []
    )
    assert (
        anon_client.patch(
            f"/api/v1/planned/{mine['id']}", json={"title": "hackeo"}, headers=headers_b
        ).status_code
        == 404
    )
