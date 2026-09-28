"""Webhook de Telegram: solo entiende el comando `/hoy`.

El token del bot hace de "secreto en la URL" (`/telegram/webhook/{token}`):
es el patrón habitual para webhooks de Telegram y evita añadir un tercer
secreto de Secret Manager solo para esto — únicamente quien conoce
`TELEGRAM_BOT_TOKEN` (nosotros, al registrar el webhook con `setWebhook`)
sabe la URL real. Una llamada con el token equivocado responde 404, igual
que si la ruta no existiera.
"""

import secrets

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from app.automation import telegram_service
from app.core.config import get_settings
from app.core.deps import DbSession
from app.models.user import User
from app.utils.timezone import today_local
from app.utils.today import build_today_summary

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook/{token}")
async def webhook(token: str, request: Request, db: DbSession):
    expected = get_settings().telegram_bot_token
    if not expected or not secrets.compare_digest(token, expected):
        raise HTTPException(404)

    update = await request.json()
    message = update.get("message") or update.get("edited_message") or {}
    chat_id = message.get("chat", {}).get("id")
    text = (message.get("text") or "").strip().lower()

    if chat_id is None or not text.startswith("/hoy"):
        return {"ok": True}  # Telegram solo necesita un 200; el resto lo ignoramos.

    user = db.scalar(select(User).where(User.telegram_chat_id == str(chat_id)))
    reply = (
        format_reply(db, user)
        if user
        else "Este chat no está vinculado a ninguna cuenta de CIMA todavía."
    )
    telegram_service.send_message(expected, str(chat_id), reply)
    return {"ok": True}


def format_reply(db: DbSession, user: User) -> str:
    summary = build_today_summary(db, user.id, today_local())
    return telegram_service.format_today_message(summary)
