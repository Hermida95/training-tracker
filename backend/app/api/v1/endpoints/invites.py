from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession
from app.core.security import generate_friendly_code
from app.models.invite import InviteCode
from app.schemas.auth import InviteCodeRead

router = APIRouter(prefix="/invites", tags=["invites"])

# Tope de códigos sin usar a la vez: evita generar cientos y repartirlos en masa.
MAX_PENDING_INVITES = 5


def _require_admin(user) -> None:
    """Solo el administrador (primer usuario de la instancia) invita gente:
    quién entra lo decide el dueño del despliegue, no cualquier invitado."""
    if not user.is_admin:
        raise HTTPException(403, "Solo el administrador puede gestionar invitaciones")


@router.get("", response_model=list[InviteCodeRead])
def list_invites(db: DbSession, user: CurrentUser):
    _require_admin(user)
    return list(
        db.scalars(
            select(InviteCode)
            .where(InviteCode.created_by_user_id == user.id)
            .order_by(InviteCode.created_at.desc())
        )
    )


@router.post("", response_model=InviteCodeRead, status_code=201)
def create_invite(db: DbSession, user: CurrentUser):
    _require_admin(user)
    pending = db.scalar(
        select(func.count())
        .select_from(InviteCode)
        .where(InviteCode.created_by_user_id == user.id, InviteCode.used_at.is_(None))
    )
    if pending >= MAX_PENDING_INVITES:
        raise HTTPException(
            409, f"Ya tienes {MAX_PENDING_INVITES} invitaciones sin usar. Comparte esas primero."
        )

    invite = InviteCode(code=generate_friendly_code(groups=2), created_by_user_id=user.id)
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite
