from tests.conftest import register_user


def _register(client, email, code=None):
    payload = {"email": email, "password": "secreta1234"}
    if code is not None:
        payload["invite_code"] = code
    return client.post("/api/v1/auth/register", json=payload)


# ---------------------------------------------------------------------------
# Invitaciones
# ---------------------------------------------------------------------------


def test_first_user_registers_without_invite(anon_client):
    assert _register(anon_client, "primero@example.com").status_code == 201


def test_second_user_needs_valid_invite(anon_client):
    headers_a = register_user(anon_client, "a@example.com")

    # Sin código -> 403 · con código inventado -> 403
    assert _register(anon_client, "b@example.com").status_code == 403
    assert _register(anon_client, "b@example.com", "XXXX-XXXX").status_code == 403

    # Con código real -> entra
    code = anon_client.post("/api/v1/invites", headers=headers_a).json()["code"]
    assert _register(anon_client, "b@example.com", code).status_code == 201


def test_invite_is_single_use_and_tolerates_formatting(anon_client):
    headers_a = register_user(anon_client, "a@example.com")
    code = anon_client.post("/api/v1/invites", headers=headers_a).json()["code"]

    # Se acepta en minúsculas, con espacios y sin guion
    sloppy = code.replace("-", " ").lower()
    assert _register(anon_client, "b@example.com", sloppy).status_code == 201

    # El mismo código ya no vale para un tercero
    assert _register(anon_client, "c@example.com", code).status_code == 403

    # Y en el listado del creador aparece como usado
    listed = anon_client.get("/api/v1/invites", headers=headers_a).json()
    assert listed[0]["used_at"] is not None


def test_only_admin_can_manage_invites(anon_client):
    headers_admin = register_user(anon_client, "admin@example.com")
    headers_amigo = register_user(anon_client, "amigo@example.com", invited_by=headers_admin)

    # El primer usuario es admin; el invitado no
    me_admin = anon_client.get("/api/v1/auth/me", headers=headers_admin).json()
    me_amigo = anon_client.get("/api/v1/auth/me", headers=headers_amigo).json()
    assert me_admin["is_admin"] is True
    assert me_amigo["is_admin"] is False

    # El invitado no puede generar ni listar invitaciones
    assert anon_client.post("/api/v1/invites", headers=headers_amigo).status_code == 403
    assert anon_client.get("/api/v1/invites", headers=headers_amigo).status_code == 403


def test_pending_invites_are_capped(anon_client):
    headers_a = register_user(anon_client, "a@example.com")
    for _ in range(5):
        assert anon_client.post("/api/v1/invites", headers=headers_a).status_code == 201
    assert anon_client.post("/api/v1/invites", headers=headers_a).status_code == 409


# ---------------------------------------------------------------------------
# Recuperación de contraseña
# ---------------------------------------------------------------------------


def test_recovery_code_resets_password_once(anon_client):
    headers = register_user(anon_client, "yo@example.com")

    me = anon_client.get("/api/v1/auth/me", headers=headers).json()
    assert me["has_recovery_code"] is False

    code = anon_client.post("/api/v1/auth/recovery-code", headers=headers).json()["recovery_code"]
    assert anon_client.get("/api/v1/auth/me", headers=headers).json()["has_recovery_code"]

    # Reset con el código (tolerando formato descuidado) -> nueva contraseña
    res = anon_client.post(
        "/api/v1/auth/reset-password",
        json={
            "email": "yo@example.com",
            "recovery_code": code.lower().replace("-", ""),
            "new_password": "nuevaclave99",
        },
    )
    assert res.status_code == 200

    # La vieja ya no vale, la nueva sí
    old = anon_client.post(
        "/api/v1/auth/login", json={"email": "yo@example.com", "password": "secreta1234"}
    )
    assert old.status_code == 401
    new = anon_client.post(
        "/api/v1/auth/login", json={"email": "yo@example.com", "password": "nuevaclave99"}
    )
    assert new.status_code == 200

    # El código era de un solo uso
    again = anon_client.post(
        "/api/v1/auth/reset-password",
        json={
            "email": "yo@example.com",
            "recovery_code": code,
            "new_password": "otraclave123",
        },
    )
    assert again.status_code == 401


def test_reset_rejects_wrong_code_and_unknown_email(anon_client):
    headers = register_user(anon_client, "yo@example.com")
    anon_client.post("/api/v1/auth/recovery-code", headers=headers)

    wrong = anon_client.post(
        "/api/v1/auth/reset-password",
        json={
            "email": "yo@example.com",
            "recovery_code": "AAAA-AAAA-AAAA",
            "new_password": "nuevaclave99",
        },
    )
    assert wrong.status_code == 401

    unknown = anon_client.post(
        "/api/v1/auth/reset-password",
        json={
            "email": "nadie@example.com",
            "recovery_code": "AAAA-AAAA-AAAA",
            "new_password": "nuevaclave99",
        },
    )
    # Mismo error que con código malo: no se filtra qué emails existen
    assert unknown.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]
