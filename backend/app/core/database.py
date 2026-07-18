from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# SQLite (usado en tests) necesita este flag porque cada request de FastAPI
# puede usar un hilo distinto al que creó la conexión.
connect_args = {"check_same_thread": False} if settings.is_sqlite else {}

engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator:
    """Dependency de FastAPI: una sesión de BD por request, cerrada al final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
