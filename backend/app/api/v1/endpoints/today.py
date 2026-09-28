import datetime

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.today import TodaySummary
from app.utils.timezone import today_local
from app.utils.today import build_today_summary

router = APIRouter(tags=["today"])


@router.get("/today", response_model=TodaySummary)
def get_today(db: DbSession, user: CurrentUser, date: datetime.date | None = None):
    """Rutina de mañana, menú vigente y sesión de hoy en una sola llamada.

    Es la misma composición que usan los recordatorios de Telegram
    (`app/utils/today.py`), aquí expuesta para el frontend.
    """
    return build_today_summary(db, user.id, date or today_local())
