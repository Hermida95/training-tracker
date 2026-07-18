import datetime

from sqlalchemy import Date
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BodyMetric(Base):
    """Una medición diaria de peso y/o cintura. Ambos campos son opcionales
    porque el usuario puede registrar solo uno de los dos en un día dado."""

    __tablename__ = "body_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[datetime.date] = mapped_column(Date, unique=True, index=True)
    weight_kg: Mapped[float | None] = mapped_column(default=None)
    waist_cm: Mapped[float | None] = mapped_column(default=None)
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.UTC)
    )
