"""Envío de mensajes por Telegram (Bot API) y su formateo.

Sin dependencias nuevas: la Bot API es un POST JSON normal, así que basta con
`urllib` de la stdlib (mismo criterio que `email_report.py` con `smtplib`).
`send_message` recibe un `sender` inyectable para poder testear el resto del
flujo (recordatorios, comando /hoy) sin golpear la red real.
"""

import json
import urllib.error
import urllib.request

from app.schemas.today import TodaySummary

TELEGRAM_API_BASE = "https://api.telegram.org"

_WEEKDAY_NAMES = [
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
]


def _default_sender(token: str, chat_id: str, text: str) -> None:
    url = f"{TELEGRAM_API_BASE}/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    request = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        if response.status != 200:
            raise urllib.error.HTTPError(
                url, response.status, "Telegram sendMessage falló", response.headers, None
            )


def send_message(token: str, chat_id: str, text: str, sender=_default_sender) -> None:
    sender(token, chat_id, text)


def _header(summary: TodaySummary) -> str:
    weekday = _WEEKDAY_NAMES[summary.date.weekday()]
    return f"CIMA — hoy {weekday} {summary.date.isoformat()}"


def format_morning_message(summary: TodaySummary) -> str:
    lines = [_header(summary), "", "Rutina de mañana:"]
    if not summary.morning_routine:
        lines.append("- Nada programado hoy")
    for h in summary.morning_routine:
        check = "✅" if h.done else "⬜"
        lines.append(f"{check} {h.name}")
    return "\n".join(lines)


def format_meal_message(summary: TodaySummary) -> str:
    lines = [_header(summary), "", "Comida:"]
    if summary.meal:
        suffix = " (adjunto en la app)" if summary.meal.has_file else ""
        lines.append(f"- {summary.meal.title}{suffix}")
        if summary.meal.text_excerpt:
            lines.append(summary.meal.text_excerpt)
    else:
        lines.append("- Sin menú subido todavía")
    return "\n".join(lines)


def format_training_message(summary: TodaySummary) -> str:
    lines = [_header(summary), "", "Entreno:"]
    t = summary.training
    if t.is_rest_day:
        lines.append(f"- {t.title} (descanso)")
    else:
        lines.append(f"- {t.title} ({t.workout_type.value if t.workout_type else 'CUSTOM'})")
        if t.periodization:
            lines.append(f"  {t.periodization.label}: {t.periodization.rir_target}")
        if t.details:
            lines.append(f"  {t.details}")
    return "\n".join(lines)


def format_today_message(summary: TodaySummary) -> str:
    """Resumen completo del día, usado por el comando `/hoy` del bot.

    Junta las tres secciones que los crons de recordatorio envían por
    separado (`format_morning_message`/`format_meal_message`/
    `format_training_message`), sin repetir la cabecera.
    """
    sections = [
        format_morning_message(summary),
        format_meal_message(summary),
        format_training_message(summary),
    ]
    body = "\n\n".join(s.split("\n\n", 1)[1] for s in sections)
    return f"{_header(summary)}\n\n{body}"
