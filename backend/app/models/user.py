import datetime

from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    password_hash: Mapped[str]
    # El administrador de la instancia (el primer usuario registrado): es el
    # único que puede generar códigos de invitación.
    is_admin: Mapped[bool] = mapped_column(default=False)
    # Hash bcrypt del código de recuperación (un solo uso). None = el usuario
    # no ha generado ninguno; si olvida la contraseña sin él, toca BD a mano.
    recovery_code_hash: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.UTC)
    )

    @property
    def has_recovery_code(self) -> bool:
        return self.recovery_code_hash is not None
