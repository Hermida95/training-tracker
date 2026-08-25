"""Informe semanal por email (Gmail SMTP).

Se dispara cada domingo desde `weekly_plan.py`, después de escribir el plan
nuevo. Usa smtplib directo con una contraseña de aplicación de Gmail —ni la
contraseña normal de la cuenta ni un servicio de terceros—, así que no añade
ninguna dependencia nueva ni cuenta que crear.

`build_report_body` es una función pura (sin red, fácil de testear); el envío
en sí usa un `sender` inyectable, igual que `coach.generate_plan(..., runner=)`.
Si el envío falla, `weekly_plan.py` lo captura y sigue: el plan ya escrito es
lo importante, el email es un extra.
"""

import datetime
import smtplib
from email.mime.text import MIMEText

from app.automation.garmin_metrics import WeeklyMetrics

GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587

_WEEKDAY_NAMES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _default_smtp_send(
    address: str, app_password: str, to_addr: str, subject: str, body_text: str
) -> None:
    msg = MIMEText(body_text, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = address
    msg["To"] = to_addr
    with smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT, timeout=20) as server:
        server.starttls()
        server.login(address, app_password)
        server.send_message(msg)


def send_weekly_email(
    address: str,
    app_password: str,
    subject: str,
    body_text: str,
    to_addr: str | None = None,
    sender=_default_smtp_send,
) -> None:
    """Envía el informe. `to_addr` por defecto es la propia cuenta (autoenvío)."""
    sender(address, app_password, to_addr or address, subject, body_text)


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
