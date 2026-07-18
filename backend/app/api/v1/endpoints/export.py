from typing import Literal

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.core.deps import DbSession
from app.schemas.stats import ExportPayload
from app.utils.export import build_export_payload, render_as_text
from app.utils.timezone import today_local

router = APIRouter(prefix="/export", tags=["export"])


@router.get("", response_model=None)
def export_month(
    db: DbSession,
    year: int | None = None,
    month: int | None = None,
    format: Literal["json", "text"] = "json",
):
    """Resumen del mes listo para copiar y pegar a un coach IA.

    `format=text` devuelve texto plano legible; `format=json` (default)
    devuelve el mismo contenido estructurado para integraciones.
    """
    today = today_local()
    payload = build_export_payload(db, year or today.year, month or today.month)
    if format == "text":
        return PlainTextResponse(render_as_text(payload))
    return payload


@router.get("/typed", response_model=ExportPayload)
def export_month_typed(db: DbSession, year: int | None = None, month: int | None = None):
    """Igual que GET /export pero con response_model tipado, útil desde clientes generados."""
    today = today_local()
    return build_export_payload(db, year or today.year, month or today.month)
