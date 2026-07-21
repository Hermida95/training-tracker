from tests.conftest import register_user


def test_register_creates_account_with_seeded_data(anon_client):
    res = anon_client.post(
        "/api/v1/auth/register", json={"email": "nuevo@example.com", "password": "secreta1234"}
    )
    assert res.status_code == 201
    body = res.json()
    assert body["user"]["email"] == "nuevo@example.com"
    headers = {"Authorization": f"Bearer {body['access_token']}"}

    # La cuenta nace con la rutina y los hábitos precargados
    habits = anon_client.get("/api/v1/habits", headers=headers).json()
    assert len(habits) == 5
    templates = anon_client.get("/api/v1/workouts/templates", headers=headers).json()
    assert len(templates) == 18


def test_register_rejects_duplicate_email(anon_client):
    payload = {"email": "dup@example.com", "password": "secreta1234"}
    assert anon_client.post("/api/v1/auth/register", json=payload).status_code == 201
    assert anon_client.post("/api/v1/auth/register", json=payload).status_code == 409


def test_login_and_me(anon_client):
    anon_client.post(
        "/api/v1/auth/register", json={"email": "yo@example.com", "password": "secreta1234"}
    )

    ok = anon_client.post(
        "/api/v1/auth/login", json={"email": "yo@example.com", "password": "secreta1234"}
    )
    assert ok.status_code == 200
    token = ok.json()["access_token"]

    me = anon_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "yo@example.com"

    bad = anon_client.post(
        "/api/v1/auth/login", json={"email": "yo@example.com", "password": "incorrecta99"}
    )
    assert bad.status_code == 401


def test_endpoints_require_auth(anon_client):
    assert anon_client.get("/api/v1/habits").status_code == 401
    assert anon_client.get("/api/v1/workouts").status_code == 401
    assert anon_client.get("/api/v1/stats/monthly").status_code == 401
    assert (
        anon_client.get("/api/v1/habits", headers={"Authorization": "Bearer basura"}).status_code
        == 401
    )


def test_users_cannot_see_each_others_data(anon_client):
    headers_a = register_user(anon_client, "a@example.com")
    headers_b = register_user(anon_client, "b@example.com")

    # A crea un hábito personalizado y una sesión de entreno
    habit = anon_client.post(
        "/api/v1/habits",
        json={"key": "estudio", "name": "Estudio", "value_type": "boolean", "active_days": [0]},
        headers=headers_a,
    ).json()
    session = anon_client.post(
        "/api/v1/workouts",
        json={"date": "2026-07-13", "workout_type": "GYM1", "exercises": []},
        headers=headers_a,
    ).json()

    # B no ve el hábito de A en su lista ni puede acceder por id
    keys_b = [h["key"] for h in anon_client.get("/api/v1/habits", headers=headers_b).json()]
    assert "estudio" not in keys_b
    assert anon_client.get(f"/api/v1/habits/{habit['id']}", headers=headers_b).status_code == 404
    assert (
        anon_client.get(f"/api/v1/workouts/{session['id']}", headers=headers_b).status_code == 404
    )
    assert (
        anon_client.delete(f"/api/v1/workouts/{session['id']}", headers=headers_b).status_code
        == 404
    )

    # Y sus stats no incluyen la sesión de A
    stats_b = anon_client.get(
        "/api/v1/stats/monthly",
        params={"year": 2026, "month": 7},
        headers=headers_b,
    ).json()
    assert stats_b["sessions_completed"] == 0
