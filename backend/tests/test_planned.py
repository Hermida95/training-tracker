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


# --- Mover / intercambiar un día del plan ---


def test_move_to_empty_day_just_relocates(client):
    planned = client.post(
        "/api/v1/planned",
        json={
            "date": "2026-08-24",
            "workout_type": "RUNNING",
            "title": "Rodaje Z2",
            "source": "ai",
        },
    ).json()

    moved = client.post(f"/api/v1/planned/{planned['id']}/move", json={"to_date": "2026-08-26"})
    assert moved.status_code == 200
    body = moved.json()
    assert len(body) == 1
    assert body[0]["id"] == planned["id"]
    assert body[0]["date"] == "2026-08-26"
    assert body[0]["title"] == "Rodaje Z2"
    assert body[0]["source"] == "manual"  # mover a mano lo marca como manual

    # El día de origen queda libre (sin plan = descanso implícito)
    assert client.get("/api/v1/planned/today", params={"date": "2026-08-24"}).json() is None


def test_move_to_occupied_day_swaps_content_keeping_dates(client):
    mon = client.post(
        "/api/v1/planned",
        json={"date": "2026-08-24", "workout_type": "RUNNING", "title": "Series 6x800m"},
    ).json()
    tue = client.post(
        "/api/v1/planned",
        json={"date": "2026-08-25", "workout_type": "GYM1", "title": "Gym A"},
    ).json()

    swapped = client.post(f"/api/v1/planned/{mon['id']}/move", json={"to_date": "2026-08-25"})
    assert swapped.status_code == 200
    body = {row["id"]: row for row in swapped.json()}
    assert len(body) == 2

    # Cada fila conserva su id y su fecha; solo cambia el contenido.
    assert body[mon["id"]]["date"] == "2026-08-24"
    assert body[mon["id"]]["title"] == "Gym A"
    assert body[mon["id"]]["workout_type"] == "GYM1"
    assert body[tue["id"]]["date"] == "2026-08-25"
    assert body[tue["id"]]["title"] == "Series 6x800m"
    assert body[tue["id"]]["workout_type"] == "RUNNING"
    assert all(row["source"] == "manual" for row in body.values())


def test_move_to_same_date_is_a_noop(client):
    planned = client.post(
        "/api/v1/planned", json={"date": "2026-08-24", "title": "Gym A", "source": "ai"}
    ).json()
    res = client.post(f"/api/v1/planned/{planned['id']}/move", json={"to_date": "2026-08-24"})
    assert res.status_code == 200
    assert res.json() == [planned]
    assert res.json()[0]["source"] == "ai"  # no se toca: no hubo cambio real


def test_move_not_found_for_other_user(client, anon_client):
    from tests.conftest import register_user

    mine = client.post("/api/v1/planned", json={"date": "2026-08-24", "title": "Mío"}).json()
    headers_b = register_user(anon_client, "otro2@example.com", invited_by=client.headers)
    res = anon_client.post(
        f"/api/v1/planned/{mine['id']}/move", json={"to_date": "2026-08-25"}, headers=headers_b
    )
    assert res.status_code == 404
