import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class InviteCode(Base):
    """Código de invitación de un solo uso.

    El registro está cerrado: salvo el primer usuario de la instancia, nadie
    puede crear cuenta sin un código válido. Los códigos los genera cualquier
    usuario con sesión (máx. 5 pendientes a la vez) y se marcan como usados al
    consumirse. Se guardan en claro a propósito: su único poder es permitir un
    registro, y el dueño necesita poder verlos para compartirlos.
    """

    __tablename__ = "invite_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(unique=True, index=True)
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    used_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.UTC)
    )
    used_at: Mapped[datetime.datetime | None] = mapped_column(default=None)
