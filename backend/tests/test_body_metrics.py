def test_upsert_metric_updates_existing_date(client):
    client.post("/api/v1/body-metrics", json={"date": "2026-07-13", "weight_kg": 80.5})
    res = client.post("/api/v1/body-metrics", json={"date": "2026-07-13", "waist_cm": 88})
    body = res.json()
    # Mismo día: el segundo POST no debe borrar el peso ya guardado
    assert body["weight_kg"] == 80.5
    assert body["waist_cm"] == 88


def test_weekly_average_groups_by_monday_start(client):
    client.post("/api/v1/body-metrics", json={"date": "2026-07-13", "weight_kg": 80.0})  # lunes
    client.post("/api/v1/body-metrics", json={"date": "2026-07-15", "weight_kg": 79.0})  # miercoles
    # lunes de la semana siguiente
    client.post("/api/v1/body-metrics", json={"date": "2026-07-20", "weight_kg": 78.0})

    res = client.get("/api/v1/body-metrics/weekly-average")
    weeks = res.json()
    assert len(weeks) == 2
    assert weeks[0]["week_start"] == "2026-07-13"
    assert weeks[0]["avg_weight_kg"] == 79.5
    assert weeks[0]["sample_count"] == 2
    assert weeks[1]["week_start"] == "2026-07-20"
    assert weeks[1]["avg_weight_kg"] == 78.0
