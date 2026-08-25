"""Macrociclo de 6 meses (26 semanas) — Fuerza + Trail/Ultra.

Fuente única de verdad del "plan maestro": el mapa semana a semana del esquema
(esquema_6_meses_hibrido_fuerza_ultra.md). Lo usan:
  - el cron de los domingos, para saber en qué semana/bloque estamos y generar
    el plan de esa semana fiel al macrociclo (ajustado a la recuperación real);
  - el bootstrap, para cargar la semana actual al arrancar.

El número de semana se calcula desde `macro_start_date` (lunes de la semana 1),
que se guarda por usuario en app_settings.
"""

import datetime
from dataclasses import dataclass

# Regla rectora del macrociclo (contexto fijo para el coach).
MACRO_RULES = """\
Macrociclo de 6 meses (26 semanas), de lo general a lo específico. Reglas fijas:
- +10% de volumen semanal como TECHO, con descarga (60-70%) cada 4 semanas
  (semanas 4, 8, 12, 16, 20, 24).
- 80/20: el 80% del kilometraje en Zona 2 conversacional. La velocidad casi no aparece.
- La fuerza va antes que la resistencia si coinciden en un día.
- El volumen de gym BAJA según sube el running (Fase 3), pero no la intensidad.
- McGill Big 3 DIARIO, con o sin dolor.
Fases: F1 Base General (sem 1-8), F2 Base Específica (sem 9-16), F3 Construcción
Específica (sem 17-24), F4 Transición/Evaluación (sem 25-26)."""

# Hallazgo del ajuste con datos reales de Garmin (25 ago 2026): las carreras
# recientes van a 155-179 ppm (umbral), no Zona 2. Prioridad de las primeras
# semanas: BAJAR intensidad, no subir volumen. Techo Z2 estimado 135-148 ppm.
FC_RECALIBRATION = """\
IMPORTANTE (recalibración con Garmin): las carreras recientes iban a intensidad
de umbral (155-179 ppm), no Zona 2. La prioridad de las primeras 3 semanas es
BAJAR la intensidad de los rodajes fáciles, no subir volumen. Techo de Zona 2
estimado: 135-148 ppm. En las semanas con tope de FC, el ritmo (min/km) es
IRRELEVANTE: solo importa no pasar de la FC tope; si hay que caminar tramos, se
camina. Se revisa el techo de FC en el check-in de la semana 4."""


@dataclass
class WeekInfo:
    week: int
    phase_block: str
    running_focus: str
    long_run: str
    gym_focus: str
    rir: str
    deload: bool = False
    fc_cap: str | None = None  # tope de FC para los rodajes, si aplica

    def to_prompt(self) -> str:
        lines = [
            f"Semana {self.week} del macrociclo · {self.phase_block}"
            + (" · SEMANA DE DESCARGA" if self.deload else ""),
            f"- Running: {self.running_focus}",
            f"- Tirada larga (sábado): {self.long_run}",
            f"- Gimnasio: {self.gym_focus} · RIR objetivo {self.rir}",
        ]
        if self.fc_cap:
            lines.append(f"- Tope de FC en rodajes: {self.fc_cap} (ritmo irrelevante)")
        return "\n".join(lines)


_FC148 = "148 ppm"

# Mapa semana a semana (sección 5 del esquema). long_run incluye el back-to-back
# del domingo cuando aplica.
_WEEKS: list[WeekInfo] = [
    WeekInfo(
        1,
        "F1·B1",
        "Recalibración: FC tope 148, ritmo irrelevante",
        "50 min",
        "Full body — reconexión",
        "3",
        fc_cap=_FC148,
    ),
    WeekInfo(2, "F1·B1", "FC tope 148 sin excepciones", "60 min", "Full body", "2", fc_cap=_FC148),
    WeekInfo(
        3,
        "F1·B1",
        "FC tope 148 + cuestas suaves jueves (única excepción)",
        "75 min",
        "Full body — semana dura",
        "1-2",
        fc_cap=_FC148,
    ),
    WeekInfo(
        4,
        "F1·B1 · DESCARGA",
        "Z2 corto + check-in: revisar techo de FC con datos",
        "45 min",
        "Descarga (-1 serie)",
        "4",
        deload=True,
    ),
    WeekInfo(5, "F1·B2", "Z2 base", "65 min", "Full body", "3"),
    WeekInfo(6, "F1·B2", "Z2 + cuestas", "75 min", "Full body", "2"),
    WeekInfo(7, "F1·B2", "Z2 + cuestas", "85 min", "Full body — semana dura", "1-2"),
    WeekInfo(8, "F1·B2 · DESCARGA", "Z2 corto", "50 min", "Descarga", "4", deload=True),
    WeekInfo(9, "F2·B3", "Desnivel real", "90 min", "Full body, empieza excéntrico", "3"),
    WeekInfo(10, "F2·B3", "Desnivel + técnico", "100 min", "Full body", "2"),
    WeekInfo(11, "F2·B3", "Desnivel + técnico", "110 min", "Full body — semana dura", "1-2"),
    WeekInfo(
        12,
        "F2·B3 · DESCARGA",
        "Suave + prueba back-to-back corta",
        "60 min + domingo 20-30 min trote suave",
        "Descarga",
        "4",
        deload=True,
    ),
    WeekInfo(
        13,
        "F2·B4",
        "Back-to-back consolidado",
        "2h + domingo 60 min fácil",
        "Baja a 2x/semana",
        "3",
    ),
    WeekInfo(14, "F2·B4", "Back-to-back", "2h15 + domingo 60-75 min", "2x/semana", "2"),
    WeekInfo(15, "F2·B4", "Back-to-back — semana dura", "2h30 + domingo 75 min", "2x/semana", "2"),
    WeekInfo(
        16,
        "F2·B4 · DESCARGA",
        "Suave",
        "1h15 + domingo libre/caminata",
        "Descarga",
        "3-4",
        deload=True,
    ),
    WeekInfo(
        17,
        "F3·B5",
        "Técnico + back-to-back",
        "2h30 + domingo 75 min",
        "Mantenimiento 2x/semana",
        "2",
    ),
    WeekInfo(18, "F3·B5", "Técnico + descensos", "2h45 + domingo 90 min", "Mantenimiento", "2"),
    WeekInfo(19, "F3·B5", "Técnico — semana dura", "3h + domingo 90 min", "Mantenimiento", "2"),
    WeekInfo(
        20, "F3·B5 · DESCARGA", "Suave", "1h30 + domingo libre", "Descarga", "3-4", deload=True
    ),
    WeekInfo(
        21, "F3·B6", "Simulación de carrera", "3h + domingo 90 min", "Mantenimiento mínimo", "2"
    ),
    WeekInfo(
        22, "F3·B6", "Simulación de carrera", "3h15 + domingo 1h45", "Mantenimiento mínimo", "2"
    ),
    WeekInfo(
        23,
        "F3·B6 · PICO",
        "Fin de semana más exigente del macrociclo",
        "3h30-4h + domingo 2h",
        "Mantenimiento mínimo",
        "2-3",
    ),
    WeekInfo(
        24,
        "F3·B6 · DESCARGA",
        "Suave",
        "1h30 + domingo libre",
        "Descarga profunda",
        "4",
        deload=True,
    ),
    WeekInfo(
        25, "F4 · Transición", "Muy suave, sensaciones", "60-75 min", "Full body ligero", "3-4"
    ),
    WeekInfo(
        26,
        "F4 · Evaluación",
        "Muy suave + check-in completo",
        "60-75 min",
        "Full body ligero",
        "3-4",
    ),
]

TOTAL_WEEKS = len(_WEEKS)


def get_week(week_number: int) -> WeekInfo:
    """Devuelve la info de la semana N (1-26), clamp fuera de rango."""
    idx = max(1, min(week_number, TOTAL_WEEKS)) - 1
    return _WEEKS[idx]


def week_number_for(macro_start: datetime.date, target_monday: datetime.date) -> int:
    """Número de semana del macrociclo para el lunes objetivo (1-based)."""
    return ((target_monday - macro_start).days // 7) + 1
