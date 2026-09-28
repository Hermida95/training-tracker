"""Endpoints que dispara Cloud Scheduler (nunca el navegador): tres crons
diarios que le escriben a cada usuario con Telegram vinculado.

Protegidos con un secreto compartido en la cabecera `X-Scheduler-Secret`
(comparación en tiempo constante) en vez de JWT: no hay usuario "logueado"
que dispare esto, es infraestructura llamando a infraestructura. El secreto
vive en Secret Manager (ver infra/terraform/secrets.tf) y llega aquí como
variable de entorno igual que el resto.
"""

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.automation import telegram_service
from app.core.config import get_settings
from app.core.deps import DbSession
from app.models.user import User
from app.utils.timezone import today_local
from app.utils.today import build_today_summary

router = APIRouter(prefix="/internal/notify", tags=["internal"])


def _verify_scheduler_secret(x_scheduler_secret: str | None = Header(default=None)) -> None:
    expected = get_settings().scheduler_shared_secret
    # Fail-closed: sin secreto configurado, el endpoint queda cerrado a cal y
    # canto (nunca "abierto por descuido" en un despliegue sin configurar).
    if not expected or not x_scheduler_secret:
        raise HTTPException(401, "No autorizado")
    if not secrets.compare_digest(x_scheduler_secret, expected):
        raise HTTPException(401, "No autorizado")


_guarded = [Depends(_verify_scheduler_secret)]


def _users_with_telegram(db: Session) -> list[User]:
    return list(db.scalars(select(User).where(User.telegram_chat_id.is_not(None))))


def _notify_all(db: Session, formatter) -> dict[str, int]:
    token = get_settings().telegram_bot_token
    if not token:
        return {"sent": 0, "failed": 0}

    today = today_local()
    sent = failed = 0
    for user in _users_with_telegram(db):
        summary = build_today_summary(db, user.id, today)
        try:
            telegram_service.send_message(token, user.telegram_chat_id, formatter(summary))
            sent += 1
        except Exception:  # noqa: BLE001 - un chat roto no debe tumbar al resto
            failed += 1
    return {"sent": sent, "failed": failed}


@router.post("/morning", dependencies=_guarded)
def notify_morning(db: DbSession):
    return _notify_all(db, telegram_service.format_morning_message)


@router.post("/meal", dependencies=_guarded)
def notify_meal(db: DbSession):
    return _notify_all(db, telegram_service.format_meal_message)


@router.post("/training", dependencies=_guarded)
def notify_training(db: DbSession):
    return _notify_all(db, telegram_service.format_training_message)
