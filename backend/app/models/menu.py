import datetime

from sqlalchemy import ForeignKey, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MenuDocument(Base):
    """El menú/plan de comidas del usuario: una foto, un PDF o texto pegado.

    El binario vive en la propia BD (LargeBinary) en vez de en un bucket:
    con el cap de 8MB por fichero y uso personal cabe de sobra en el tier
    gratuito de Neon (0.5GB) y evita añadir GCS + URLs firmadas solo para
    esto. Si algún día se sube mucho volumen, el punto de corte natural es
    mover `file_data` a un bucket y dejar aquí la referencia.
    """

    __tablename__ = "menu_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str]
    # None en menús solo-texto; si hay fichero, uno de los ALLOWED_MENU_TYPES.
    content_type: Mapped[str | None] = mapped_column(default=None)
    file_data: Mapped[bytes | None] = mapped_column(LargeBinary, default=None)
    file_size: Mapped[int] = mapped_column(default=0)
    text_content: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.UTC)
    )
