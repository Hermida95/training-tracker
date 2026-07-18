from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AppSetting(Base):
    """Tabla clave/valor genérica para configuración editable en runtime.

    Se usa para: intervalo de la alarma antisedentarismo, ventana horaria,
    y la fecha de inicio del programa de periodización (necesaria para saber
    en qué semana del ciclo de 4 estamos). Todo como texto para simplicidad;
    cada consumidor castea al tipo que espera.
    """

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[str] = mapped_column()
