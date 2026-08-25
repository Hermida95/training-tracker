"""Extrae métricas de recuperación y actividades de los últimos 7 días de Garmin.

Usa `garminconnect` (basado en garth). La autenticación es por **token store**:
un directorio con los tokens OAuth que se generan una vez con login manual y
duran meses. En el cron ese directorio se restaura desde un secreto (ver
AUTOMATION.md). Nunca se guarda ni usa la contraseña aquí.

El diseño es defensivo: cada métrica va en su try/except, porque no todos los
dispositivos Garmin reportan todo (readiness/HRV requieren relojes recientes).
Lo que no esté disponible se omite del resumen en vez de romper el proceso.

Además de recuperación (cómo estás), se extraen las actividades reales
registradas (qué hiciste) para que el coach pueda comparar lo planificado
contra lo real: si te saltaste una sesión, corriste más de lo previsto, etc.
"""

import datetime
import os
import statistics
from dataclasses import dataclass, field


@dataclass
class ActivitySummary:
    """Una actividad real registrada en Garmin (lo que REALMENTE se hizo)."""

    date: str | None
    activity_type: str
    name: str | None = None
    duration_min: float | None = None
    distance_km: float | None = None
    avg_hr: float | None = None
    pace_min_km: float | None = None
    elevation_gain_m: float | None = None

    def to_prompt_line(self) -> str:
        parts = [self.date or "?", self.activity_type]
        if self.name:
            parts.append(self.name)
        if self.duration_min is not None:
            parts.append(f"{self.duration_min:.0f} min")
        if self.distance_km is not None:
            parts.append(f"{self.distance_km} km")
        if self.pace_min_km is not None:
            minutes, seconds = divmod(round(self.pace_min_km * 60), 60)
            parts.append(f"ritmo {minutes}:{seconds:02d}/km")
        if self.avg_hr is not None:
            parts.append(f"FC media {self.avg_hr:.0f}")
        if self.elevation_gain_m is not None:
            parts.append(f"{self.elevation_gain_m:.0f} m desnivel+")
        return "- " + " · ".join(str(p) for p in parts)


@dataclass
class WeeklyMetrics:
    hrv_status: str | None = None
    hrv_weekly_avg_ms: float | None = None
    sleep_score_avg: float | None = None
    training_readiness_avg: float | None = None
    training_load_acute: float | None = None
    training_status: str | None = None
    resting_hr_avg: float | None = None
    recent_activities: list[ActivitySummary] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_prompt_summary(self) -> str:
        """Texto legible que se le pasa al coach IA."""
        lines = ["Métricas Garmin de los últimos 7 días:"]
        if self.hrv_status or self.hrv_weekly_avg_ms:
            lines.append(
                f"- HRV: estado {self.hrv_status or '?'}, media semanal "
                f"{self.hrv_weekly_avg_ms or '?'} ms"
            )
        if self.sleep_score_avg is not None:
            lines.append(f"- Calidad de sueño media: {self.sleep_score_avg:.0f}/100")
        if self.training_readiness_avg is not None:
            lines.append(f"- Readiness medio: {self.training_readiness_avg:.0f}/100")
        if self.training_load_acute is not None or self.training_status:
            lines.append(
                f"- Carga de entrenamiento: {self.training_load_acute or '?'} "
                f"(estado: {self.training_status or '?'})"
            )
        if self.resting_hr_avg is not None:
            lines.append(f"- FC en reposo media: {self.resting_hr_avg:.0f} ppm")
        if len(lines) == 1:
            lines.append("- (sin métricas disponibles esta semana)")
        for note in self.notes:
            lines.append(f"- Aviso: {note}")

        lines.append("\nActividades reales registradas (lo que REALMENTE hizo, no lo planificado):")
        if self.recent_activities:
            lines.extend(a.to_prompt_line() for a in self.recent_activities)
        else:
            lines.append("- (sin actividades registradas esta semana)")

        return "\n".join(lines)


def _last_7_dates(today: datetime.date) -> list[datetime.date]:
    return [today - datetime.timedelta(days=i) for i in range(1, 8)]


def _parse_activity(raw: dict) -> ActivitySummary | None:
    """Convierte el JSON crudo de una actividad de Garmin Connect en un resumen.

    Función pura (sin llamadas de red) para poder testearla sin mockear la API.
    Devuelve None si el dict no tiene ni lo mínimo (tipo de actividad).
    """
    activity_type = ((raw.get("activityType") or {}).get("typeKey")) or None
    if not activity_type:
        return None

    start = raw.get("startTimeLocal") or ""
    date = start.split(" ")[0] if start else None

    duration_s = raw.get("duration")
    duration_min = round(duration_s / 60, 1) if isinstance(duration_s, int | float) else None

    distance_m = raw.get("distance")
    distance_km = round(distance_m / 1000, 2) if isinstance(distance_m, int | float) else None

    # Ritmo min/km: solo tiene sentido con distancia real recorrida (descarta
    # gym/otras actividades sin desplazamiento, que a veces llevan distance=0).
    pace_min_km = None
    if duration_min and distance_km and distance_km >= 0.3:
        pace_min_km = round(duration_min / distance_km, 2)

    avg_hr = raw.get("averageHR")
    elevation_gain = raw.get("elevationGain")

    return ActivitySummary(
        date=date,
        activity_type=activity_type,
        name=raw.get("activityName"),
        duration_min=duration_min,
        distance_km=distance_km,
        avg_hr=avg_hr if isinstance(avg_hr, int | float) else None,
        pace_min_km=pace_min_km,
        elevation_gain_m=elevation_gain if isinstance(elevation_gain, int | float) else None,
    )


def collect(tokenstore: str, today: datetime.date | None = None) -> WeeklyMetrics:
    from garminconnect import Garmin

    today = today or datetime.date.today()
    api = Garmin()
    api.login(tokenstore)  # reanuda sesión desde los tokens del directorio

    m = WeeklyMetrics()
    dates = _last_7_dates(today)

    # --- HRV (último dato semanal disponible) ---
    for d in dates:
        try:
            hrv = api.get_hrv_data(d.isoformat())
            summ = (hrv or {}).get("hrvSummary") or {}
            if summ:
                m.hrv_status = summ.get("status")
                m.hrv_weekly_avg_ms = summ.get("weeklyAvg") or summ.get("lastNightAvg")
                break
        except Exception:  # noqa: BLE001 - métrica opcional
            continue

    # --- Sueño (media de los scores diarios) ---
    sleep_scores = []
    for d in dates:
        try:
            sleep = api.get_sleep_data(d.isoformat()) or {}
            dto = sleep.get("dailySleepDTO") or {}
            score = (dto.get("sleepScores") or {}).get("overall", {}).get("value")
            if score is None:
                score = dto.get("sleepScoreValue") or sleep.get("sleepScore")
            if isinstance(score, int | float):
                sleep_scores.append(score)
        except Exception:  # noqa: BLE001
            continue
    if sleep_scores:
        m.sleep_score_avg = statistics.mean(sleep_scores)

    # --- Readiness (media diaria) ---
    readiness = []
    for d in dates:
        try:
            tr = api.get_training_readiness(d.isoformat())
            item = tr[0] if isinstance(tr, list) and tr else tr
            score = (item or {}).get("score") if isinstance(item, dict) else None
            if isinstance(score, int | float):
                readiness.append(score)
        except Exception:  # noqa: BLE001
            continue
    if readiness:
        m.training_readiness_avg = statistics.mean(readiness)

    # --- Carga de entrenamiento / estado (último disponible) ---
    for d in dates:
        try:
            ts = api.get_training_status(d.isoformat()) or {}
            most_recent = ts.get("mostRecentTrainingStatus") or {}
            details = (most_recent.get("latestTrainingStatusData") or {}).values()
            for v in details:
                m.training_load_acute = v.get("acuteTrainingLoad") or m.training_load_acute
                m.training_status = v.get("trainingStatusFeedbackPhrase") or m.training_status
            if m.training_load_acute or m.training_status:
                break
        except Exception:  # noqa: BLE001
            continue

    # --- FC en reposo (media diaria) ---
    rhr = []
    for d in dates:
        try:
            row = api.get_rhr_day(d.isoformat()) or {}
            metrics = (row.get("allMetrics") or {}).get("metricsMap") or {}
            values = metrics.get("WELLNESS_RESTING_HEART_RATE") or []
            if values and isinstance(values[0], dict):
                v = values[0].get("value")
                if isinstance(v, int | float):
                    rhr.append(v)
        except Exception:  # noqa: BLE001
            continue
    if rhr:
        m.resting_hr_avg = statistics.mean(rhr)

    # --- Actividades reales (planificado vs. lo que de verdad se hizo) ---
    try:
        raw_activities = api.get_activities_by_date(dates[-1].isoformat(), dates[0].isoformat())
        for raw in raw_activities or []:
            parsed = _parse_activity(raw)
            if parsed:
                m.recent_activities.append(parsed)
        m.recent_activities.sort(key=lambda a: a.date or "")
    except Exception as e:  # noqa: BLE001 - métrica opcional
        m.notes.append(f"no se pudieron leer las actividades: {e}")

    return m


def stub() -> WeeklyMetrics:
    """Métricas de ejemplo para probar el pipeline sin Garmin (--stub-metrics)."""
    return WeeklyMetrics(
        hrv_status="balanced",
        hrv_weekly_avg_ms=58,
        sleep_score_avg=74,
        training_readiness_avg=68,
        training_load_acute=420,
        training_status="Productive",
        resting_hr_avg=52,
        recent_activities=[
            ActivitySummary(
                date="2026-08-18",
                activity_type="running",
                name="Rodaje Z2",
                duration_min=40,
                distance_km=8.0,
                avg_hr=148,
                pace_min_km=5.0,
            ),
            ActivitySummary(
                date="2026-08-20",
                activity_type="strength_training",
                name="Gym A",
                duration_min=55,
                avg_hr=118,
            ),
        ],
        notes=["datos de ejemplo (stub), no reales"],
    )


def tokenstore_path() -> str:
    return os.path.expanduser(os.getenv("GARMINTOKENS", "~/.garminconnect"))
