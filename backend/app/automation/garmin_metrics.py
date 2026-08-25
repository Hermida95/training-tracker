"""Extrae métricas de recuperación de los últimos 7 días desde Garmin Connect.

Usa `garminconnect` (basado en garth). La autenticación es por **token store**:
un directorio con los tokens OAuth que se generan una vez con login manual y
duran meses. En el cron ese directorio se restaura desde un secreto (ver
AUTOMATION.md). Nunca se guarda ni usa la contraseña aquí.

El diseño es defensivo: cada métrica va en su try/except, porque no todos los
dispositivos Garmin reportan todo (readiness/HRV requieren relojes recientes).
Lo que no esté disponible se omite del resumen en vez de romper el proceso.
"""

import datetime
import os
import statistics
from dataclasses import dataclass, field


@dataclass
class WeeklyMetrics:
    hrv_status: str | None = None
    hrv_weekly_avg_ms: float | None = None
    sleep_score_avg: float | None = None
    training_readiness_avg: float | None = None
    training_load_acute: float | None = None
    training_status: str | None = None
    resting_hr_avg: float | None = None
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
        return "\n".join(lines)


def _last_7_dates(today: datetime.date) -> list[datetime.date]:
    return [today - datetime.timedelta(days=i) for i in range(1, 8)]


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
        notes=["datos de ejemplo (stub), no reales"],
    )


def tokenstore_path() -> str:
    return os.path.expanduser(os.getenv("GARMINTOKENS", "~/.garminconnect"))
