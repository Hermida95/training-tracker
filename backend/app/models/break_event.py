import datetime
import enum

from sqlalchemy import DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BreakStatus(str, enum.Enum):
    PENDING = "pending"
    DONE = "done"
    POSTPONED = "postponed"


class BreakEvent(Base):
    """Una pausa activa programada por la alarma antisedentarismo.

    El *scheduling* real (cuándo suena) vive en el service worker del frontend,
    que calcula los huecos de 45-50 min dentro de L-V 08:30-15:00 sin depender
    del backend (ver README: estrategia de notificaciones). Este modelo es el
    registro histórico de lo que pasó con cada pausa, que la app crea/actualiza
    cuando el usuario pulsa "Hecho" o "Posponer" en la notificación.
    """

    __tablename__ = "break_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    scheduled_for: Mapped[datetime.datetime] = mapped_column(DateTime, index=True)
    status: Mapped[BreakStatus] = mapped_column(
        Enum(BreakStatus, native_enum=False, length=20), default=BreakStatus.PENDING
    )
    responded_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, default=None)
    postponed_from_id: Mapped[int | None] = mapped_column(default=None)
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.UTC)
    )
