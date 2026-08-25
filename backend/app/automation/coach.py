"""Genera el plan de la semana con Claude, usando Claude Code en modo headless.

Se ejecuta `claude -p` (Claude Code sin interfaz) autenticado con el token
OAuth de la suscripción del usuario (variable CLAUDE_CODE_OAUTH_TOKEN), de
forma que el coste va dentro del plan Pro y NO se factura API aparte.

Como no usamos el tool-calling estricto de la API, forzamos el JSON con el
prompt y lo validamos aquí; si Claude devuelve algo que no cuadra, se reintenta
una vez con un recordatorio del formato.
"""

import datetime
import json
import subprocess

from app.automation.garmin_metrics import WeeklyMetrics
from app.models.workout import WorkoutType

# Tipos válidos que el plan puede asignar a un día (o null para descanso).
_VALID_TYPES = {t.value for t in WorkoutType} | {None}

SYSTEM_CONTEXT = """\
Eres el entrenador personal de Miguel. Objetivo del bloque: base aeróbica y
volumen de trail/ultra manteniendo y subiendo fuerza (plan híbrido Fuerza +
Trail/Ultra, fase de base). Reglas innegociables:
- 80/20: la gran mayoría de la carrera es Zona 2 (fácil, poder hablar).
- Subida de volumen semanal suave (<=10%), con descarga cada 4 semanas.
- La fuerza no se sacrifica; el viernes es empuje/hombro + core con piernas
  descargadas para dejar el sábado (tirada larga) con piernas frescas.
Estructura tipo de la semana:
- Lunes: Gym A (fuerza tren inferior + empuje)  -> workout_type "GYM1"
- Martes: rodaje fácil corto Z2                  -> workout_type "RUNNING"
- Miércoles: Gym B (cadena posterior + tracción) -> workout_type "GYM2"
- Jueves: rodaje fácil medio (cuestas suaves)    -> workout_type "RUNNING"
- Viernes: Gym C (empuje/hombro + core)          -> workout_type "GYM3"
- Sábado: TIRADA LARGA Z2 (sesión clave)         -> workout_type "RUNNING"
- Domingo: descanso activo (paseo + McGill Big 3)-> workout_type null
Ajusta la carga de la semana a las métricas de recuperación: si HRV/readiness/
sueño están bajos o la carga aguda alta, baja volumen e intensidad (más Z2,
menos series/peso, o convierte un rodaje en descanso). Si están altos, progresa
con prudencia. Los ejercicios concretos de gym ya están en la app; tú decides
el ENFOQUE y los tiempos de carrera, no listas de ejercicios.
"""

OUTPUT_INSTRUCTIONS = """\
Devuelve EXCLUSIVAMENTE un objeto JSON válido (sin texto antes ni después, sin
markdown) con esta forma EXACTA:
{
  "days": [
    {
      "weekday": 0,                 // 0=Lunes ... 6=Domingo
      "workout_type": "GYM1",       // "GYM1"|"GYM2"|"GYM3"|"RUNNING"|null
      "title": "Gym A · fuerza",    // <=120 caracteres
      "details": "RIR 2. ..."       // 1-2 frases con el enfoque/tiempos
    }
    // ... exactamente 7 objetos, weekday de 0 a 6, uno por día
  ],
  "coach_note": "1-2 frases resumiendo el porqué del ajuste de esta semana"
}
"""


def _build_prompt(metrics: WeeklyMetrics, week_start: datetime.date) -> str:
    return (
        f"{SYSTEM_CONTEXT}\n\n{metrics.to_prompt_summary()}\n\n"
        f"Planifica la semana que empieza el lunes {week_start.isoformat()}.\n\n"
        f"{OUTPUT_INSTRUCTIONS}"
    )


def _run_claude(prompt: str) -> str:
    """Ejecuta Claude Code headless y devuelve el texto de la respuesta."""
    proc = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "json"],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude -p falló ({proc.returncode}): {proc.stderr[:500]}")
    # --output-format json envuelve la respuesta; el texto está en .result
    try:
        envelope = json.loads(proc.stdout)
        return envelope.get("result", proc.stdout)
    except json.JSONDecodeError:
        return proc.stdout


def _extract_json(text: str) -> dict:
    """Saca el objeto JSON del texto (tolera fences ```json o texto alrededor)."""
    text = text.strip()
    if "```" in text:
        # quita fences de markdown si los hubiera
        parts = text.split("```")
        for part in parts:
            part = part.removeprefix("json").strip()
            if part.startswith("{"):
                text = part
                break
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("La respuesta no contiene JSON")
    return json.loads(text[start : end + 1])


def _validate(plan: dict) -> None:
    days = plan.get("days")
    if not isinstance(days, list) or len(days) != 7:
        raise ValueError("Se esperaban exactamente 7 días")
    seen = set()
    for d in days:
        wd = d.get("weekday")
        if wd not in range(7) or wd in seen:
            raise ValueError(f"weekday inválido o repetido: {wd}")
        seen.add(wd)
        if d.get("workout_type") not in _VALID_TYPES:
            raise ValueError(f"workout_type inválido: {d.get('workout_type')}")
        if not d.get("title"):
            raise ValueError("Falta title en un día")


def generate_plan(metrics: WeeklyMetrics, week_start: datetime.date, runner=_run_claude) -> dict:
    """Devuelve el plan validado. `runner` es inyectable para tests."""
    prompt = _build_prompt(metrics, week_start)
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            raw = runner(prompt if attempt == 0 else prompt + "\n\nRECUERDA: solo el JSON exacto.")
            plan = _extract_json(raw)
            _validate(plan)
            return plan
        except (ValueError, json.JSONDecodeError) as e:
            last_error = e
    raise RuntimeError(f"Claude no devolvió un plan válido tras 2 intentos: {last_error}")
