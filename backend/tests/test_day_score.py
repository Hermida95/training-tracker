def _create_habit(client, key: str, days: list[int]) -> int:
    res = client.post(
        "/api/v1/habits",
        json={"key": key, "name": key, "value_type": "boolean", "active_days": days},
    )
    return res.json()["id"]


ALL_DAYS = [0, 1, 2, 3, 4, 5, 6]


def test_perfect_day_gives_three_points(client):
    a = _create_habit(client, "a", ALL_DAYS)
    b = _create_habit(client, "b", ALL_DAYS)
    for habit_id in (a, b):
        client.post(f"/api/v1/habits/{habit_id}/logs", json={"date": "2026-07-13", "done": True})

    score = client.get("/api/v1/habits/score", params={"date": "2026-07-13"}).json()
    assert score["completion_rate"] == 1.0
    assert score["points"] == 3
    assert score["tier"] == "perfect"
    assert score["streak"] == 1


def test_partial_day_tiers(client):
    ids = [_create_habit(client, f"h{i}", ALL_DAYS) for i in range(4)]

    # 3 de 4 -> 75% -> 2 puntos
    for habit_id in ids[:3]:
        client.post(f"/api/v1/habits/{habit_id}/logs", json={"date": "2026-07-13", "done": True})
    score = client.get("/api/v1/habits/score", params={"date": "2026-07-13"}).json()
    assert score["points"] == 2
    assert score["tier"] == "great"

    # 2 de 4 -> 50% -> 1 punto
    for habit_id in ids[:2]:
        client.post(f"/api/v1/habits/{habit_id}/logs", json={"date": "2026-07-14", "done": True})
    score = client.get("/api/v1/habits/score", params={"date": "2026-07-14"}).json()
    assert score["points"] == 1
    assert score["tier"] == "half"

    # 1 de 4 -> 25% -> 0 puntos
    client.post(f"/api/v1/habits/{ids[0]}/logs", json={"date": "2026-07-15", "done": True})
    score = client.get("/api/v1/habits/score", params={"date": "2026-07-15"}).json()
    assert score["points"] == 0
    assert score["tier"] == "missed"


def test_streak_survives_great_day_but_breaks_on_missed(client):
    ids = [_create_habit(client, f"h{i}", ALL_DAYS) for i in range(4)]

    # Lunes 13: 4/4 perfecto · Martes 14: 3/4 great -> racha 2
    for habit_id in ids:
        client.post(f"/api/v1/habits/{habit_id}/logs", json={"date": "2026-07-13", "done": True})
    for habit_id in ids[:3]:
        client.post(f"/api/v1/habits/{habit_id}/logs", json={"date": "2026-07-14", "done": True})

    score = client.get("/api/v1/habits/score", params={"date": "2026-07-14"}).json()
    assert score["streak"] == 2

    # Miércoles 15: 1/4 missed -> el jueves la racha vuelve a empezar
    client.post(f"/api/v1/habits/{ids[0]}/logs", json={"date": "2026-07-15", "done": True})
    for habit_id in ids:
        client.post(f"/api/v1/habits/{habit_id}/logs", json={"date": "2026-07-16", "done": True})

    score = client.get("/api/v1/habits/score", params={"date": "2026-07-16"}).json()
    assert score["streak"] == 1


def test_pending_today_does_not_break_streak(client):
    habit_id = _create_habit(client, "a", ALL_DAYS)
    client.post(f"/api/v1/habits/{habit_id}/logs", json={"date": "2026-07-13", "done": True})

    # El día 14 aún sin registrar: la racha de ayer se mantiene visible
    score = client.get("/api/v1/habits/score", params={"date": "2026-07-14"}).json()
    assert score["tier"] == "missed"
    assert score["streak"] == 1


def test_rest_day_is_neutral(client):
    # Hábito solo L-V: el sábado no hay nada programado -> "rest", sin romper racha
    habit_id = _create_habit(client, "laborables", [0, 1, 2, 3, 4])
    client.post(f"/api/v1/habits/{habit_id}/logs", json={"date": "2026-07-17", "done": True})

    saturday = client.get("/api/v1/habits/score", params={"date": "2026-07-18"}).json()
    assert saturday["tier"] == "rest"
    assert saturday["due_count"] == 0
    assert saturday["streak"] == 1  # la del viernes sigue viva


def test_score_history_returns_one_entry_per_day(client):
    habit_id = _create_habit(client, "a", ALL_DAYS)
    client.post(f"/api/v1/habits/{habit_id}/logs", json={"date": "2026-07-15", "done": True})

    history = client.get(
        "/api/v1/habits/score/history", params={"end": "2026-07-16", "days": 7}
    ).json()
    assert len(history) == 7
    # Orden cronológico ascendente, terminando en 'end'
    assert history[0]["date"] == "2026-07-10"
    assert history[-1]["date"] == "2026-07-16"
    # El día con el hábito hecho es perfecto; el resto, fallados
    perfect = next(d for d in history if d["date"] == "2026-07-15")
    assert perfect["tier"] == "perfect"


def test_monthly_stats_include_points(client):
    habit_id = _create_habit(client, "a", ALL_DAYS)
    client.post(f"/api/v1/habits/{habit_id}/logs", json={"date": "2026-07-13", "done": True})

    stats = client.get("/api/v1/stats/monthly", params={"year": 2026, "month": 7}).json()
    assert stats["perfect_days"] == 1
    assert stats["points_total"] == 3
