import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# BD SQLite en memoria por test: rápida y aislada, tal y como pide el spec
# ("SQLite para tests"). StaticPool para que todas las conexiones de un mismo
# test compartan la misma BD en memoria (si no, cada conexión ve una BD vacía).
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture()
def db_session():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def register_user(client: TestClient, email: str = "test@example.com") -> dict[str, str]:
    """Registra un usuario y devuelve los headers de Authorization listos para usar."""
    res = client.post("/api/v1/auth/register", json={"email": email, "password": "secreta1234"})
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture()
def anon_client(db_session):
    """Cliente sin autenticar, para tests de auth y de acceso denegado."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def client(anon_client):
    """Cliente con un usuario registrado y su token ya puesto en los headers.

    El registro siembra los hábitos por defecto (como en producción), pero aquí
    se borran para que cada test parta de una cuenta limpia y los tests
    anteriores al multiusuario sigan valiendo sin cambios. La siembra en sí
    se cubre en tests/test_auth.py.
    """
    anon_client.headers.update(register_user(anon_client))
    for habit in anon_client.get("/api/v1/habits").json():
        anon_client.delete(f"/api/v1/habits/{habit['id']}")
    return anon_client
