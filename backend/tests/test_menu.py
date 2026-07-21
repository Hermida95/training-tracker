from tests.conftest import register_user

# PNG 1x1 válido (cabecera real, suficiente para el roundtrip)
TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c626001000000ffff03000006000557bfabd40000000049454e44ae426082"
)


def test_upload_text_menu_and_list(client):
    res = client.post(
        "/api/v1/menu",
        data={"title": "Semana 1", "text_content": "Lunes: pollo con arroz\nMartes: salmón"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["title"] == "Semana 1"
    assert body["content_type"] is None
    assert "pollo" in body["text_content"]

    listed = client.get("/api/v1/menu").json()
    assert len(listed) == 1


def test_upload_image_and_download_roundtrip(client):
    res = client.post(
        "/api/v1/menu",
        data={"title": "Menú del nutricionista"},
        files={"file": ("menu.png", TINY_PNG, "image/png")},
    )
    assert res.status_code == 201
    menu_id = res.json()["id"]
    assert res.json()["file_size"] == len(TINY_PNG)

    file_res = client.get(f"/api/v1/menu/{menu_id}/file")
    assert file_res.status_code == 200
    assert file_res.headers["content-type"] == "image/png"
    assert file_res.headers["x-content-type-options"] == "nosniff"
    assert file_res.content == TINY_PNG


def test_upload_rejects_bad_type_and_empty(client):
    svg = client.post(
        "/api/v1/menu",
        data={"title": "Malicioso"},
        files={"file": ("evil.svg", b"<svg onload=alert(1)>", "image/svg+xml")},
    )
    assert svg.status_code == 415

    empty = client.post("/api/v1/menu", data={"title": "Vacío"})
    assert empty.status_code == 422


def test_upload_rejects_oversize_file(client):
    too_big = b"x" * (8 * 1024 * 1024 + 1)
    res = client.post(
        "/api/v1/menu",
        data={"title": "Gigante"},
        files={"file": ("big.png", too_big, "image/png")},
    )
    assert res.status_code == 413


def test_menu_is_private_per_user(client, anon_client):
    created = client.post(
        "/api/v1/menu", data={"title": "Mi menú", "text_content": "secreto"}
    ).json()

    headers_b = register_user(anon_client, "fisgona@example.com", invited_by=client.headers)
    assert anon_client.get("/api/v1/menu", headers=headers_b).json() == []
    assert (
        anon_client.get(f"/api/v1/menu/{created['id']}/file", headers=headers_b).status_code == 404
    )
    assert anon_client.delete(f"/api/v1/menu/{created['id']}", headers=headers_b).status_code == 404


def test_auth_rate_limit_returns_429(anon_client):
    for _ in range(10):
        anon_client.post(
            "/api/v1/auth/login", json={"email": "x@example.com", "password": "loquesea1"}
        )
    res = anon_client.post(
        "/api/v1/auth/login", json={"email": "x@example.com", "password": "loquesea1"}
    )
    assert res.status_code == 429
