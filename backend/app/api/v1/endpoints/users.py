from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.auth import UserRead
from app.schemas.user import TelegramLinkIn

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/me/telegram", response_model=UserRead)
def link_telegram(data: TelegramLinkIn, db: DbSession, user: CurrentUser):
    """Vincula (o, con chat_id=null, desvincula) el chat de Telegram del usuario.

    Ver README → "Recordatorios por Telegram" para cómo obtener el chat_id
    con @userinfobot. A partir de aquí, los cron de recordatorios
    (`/internal/notify/*`) le escriben a este chat.
    """
    user.telegram_chat_id = data.chat_id
    db.commit()
    db.refresh(user)
    return user
