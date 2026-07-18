import datetime

from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.core.deps import DbSession
from app.crud import break_event as crud
from app.schemas.break_event import (
    BreakConfig,
    BreakEventCreate,
    BreakEventRead,
)
from app.utils.app_settings import (
    BREAK_INTERVAL_KEY,
    BREAK_WINDOW_END_KEY,
    BREAK_WINDOW_START_KEY,
    get_setting,
    set_setting,
)

router = APIRouter(prefix="/breaks", tags=["breaks"])
settings = get_settings()


@router.get("/config", response_model=BreakConfig)
def get_config(db: DbSession):
    """Config que el service worker lee al arrancar para programar las notificaciones locales.

    Los valores por defecto vienen de las env vars; si el usuario los cambió
    desde Ajustes, se guardan en `app_settings` y prevalecen sobre el default.
    """
    return BreakConfig(
        interval_minutes=int(
            get_setting(db, BREAK_INTERVAL_KEY, str(settings.break_interval_minutes))
        ),
        window_start=get_setting(db, BREAK_WINDOW_START_KEY, settings.break_window_start),
        window_end=get_setting(db, BREAK_WINDOW_END_KEY, settings.break_window_end),
        timezone=settings.app_timezone,
    )


@router.put("/config", response_model=BreakConfig)
def update_config(data: BreakConfig, db: DbSession):
    set_setting(db, BREAK_INTERVAL_KEY, str(data.interval_minutes))
    set_setting(db, BREAK_WINDOW_START_KEY, data.window_start)
    set_setting(db, BREAK_WINDOW_END_KEY, data.window_end)
    return get_config(db)


@router.get("", response_model=list[BreakEventRead])
def list_breaks(
    db: DbSession,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
):
    return crud.list_breaks(db, start, end)


@router.post("", response_model=BreakEventRead, status_code=201)
def create_break(data: BreakEventCreate, db: DbSession):
    """El service worker llama aquí justo cuando dispara una notificación,
    para dejar constancia de que la pausa se programó (queda en PENDING
    hasta que el usuario responda "Hecho" o "Posponer")."""
    return crud.create_break(db, data)


@router.post("/{break_id}/done", response_model=BreakEventRead)
def mark_done(break_id: int, db: DbSession):
    event = crud.get_break(db, break_id)
    if not event:
        raise HTTPException(404, "Pausa no encontrada")
    return crud.mark_done(db, event)


@router.post("/{break_id}/postpone", response_model=BreakEventRead)
def postpone(break_id: int, db: DbSession, minutes: int = 5):
    event = crud.get_break(db, break_id)
    if not event:
        raise HTTPException(404, "Pausa no encontrada")
    return crud.postpone(db, event, minutes)
