from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession
from app.core.security import generate_friendly_code
from app.models.invite import InviteCode
from app.schemas.auth import InviteCodeRead

router = APIRouter(prefix="/invites", tags=["invites"])

# Tope de códigos sin usar por usuario: puedes invitar a quien quieras, pero
# nadie puede generar cientos de códigos y repartirlos en masa.
MAX_PENDING_INVITES = 5


@router.get("", response_model=list[InviteCodeRead])
def list_invites(db: DbSession, user: CurrentUser):
    return list(
        db.scalars(
            select(InviteCode)
            .where(InviteCode.created_by_user_id == user.id)
            .order_by(InviteCode.created_at.desc())
        )
    )


@router.post("", response_model=InviteCodeRead, status_code=201)
def create_invite(db: DbSession, user: CurrentUser):
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
