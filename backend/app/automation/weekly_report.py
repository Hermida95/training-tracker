"""Texto del informe semanal (entrega por Telegram, ver `weekly_plan.py`).

Antes se enviaba por Gmail SMTP; se cambió a Telegram para reutilizar el
mismo bot y token que los recordatorios diarios (`app/automation/
telegram_service.py`) en vez de mantener una segunda credencial (contraseña
de aplicación de Gmail) que además no daba ningún aviso claro si fallaba.

`build_report_body` es una función pura (sin red, fácil de testear); el envío
en sí lo hace `weekly_plan.py` con `telegram_service.send_message`. Si el
envío falla, `weekly_plan.py` lo captura y sigue: el plan ya escrito es lo
importante, el informe es un extra.
"""

import datetime

from app.automation.garmin_metrics import WeeklyMetrics

_WEEKDAY_NAMES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def build_report_body(
    metrics: WeeklyMetrics,
    plan: dict,
    week_start: datetime.date,
    planned_count: int,
    completed_count: int,
) -> str:
    """Compone el texto del informe: cómo fue la semana que termina + el
    ajuste decidido para la que empieza. `planned_count`/`completed_count`
    son de la semana ANTERIOR a `week_start` (que es el lunes que viene)."""
    lines = [f"Informe semanal CIMA — semana del {week_start.isoformat()}", ""]

    lines.append("Cómo fue la semana que termina:")
    if planned_count:
        lines.append(f"- Entrenos completados: {completed_count}/{planned_count} planificados")
    else:
        lines.append(f"- Entrenos completados: {completed_count} (sin plan generado esa semana)")

    real_km = round(sum(a.distance_km for a in metrics.recent_activities if a.distance_km), 1)
    if real_km:
        lines.append(f"- Km reales corridos: {real_km} km")

    recovery_bits = []
    if metrics.hrv_status:
        recovery_bits.append(f"HRV {metrics.hrv_status}")
    if metrics.sleep_score_avg is not None:
        recovery_bits.append(f"sueño {metrics.sleep_score_avg:.0f}/100")
    if metrics.resting_hr_avg is not None:
        recovery_bits.append(f"FC reposo {metrics.resting_hr_avg:.0f}")
    if recovery_bits:
        lines.append(f"- Recuperación: {', '.join(recovery_bits)}")

    lines.append("")
    lines.append("Ajuste para la semana que empieza:")
    lines.append(plan.get("coach_note") or "(sin nota del coach)")

    lines.append("")
    lines.append("Los próximos 7 días:")
    for d in sorted(plan.get("days", []), key=lambda x: x["weekday"]):
        kind = d.get("workout_type") or "descanso"
        lines.append(f"- {_WEEKDAY_NAMES[d['weekday']]}: {d['title']} ({kind})")

    return "\n".join(lines)
