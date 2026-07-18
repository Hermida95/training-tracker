import datetime
from collections import defaultdict

from app.models.body_metric import BodyMetric
from app.schemas.body_metric import WeeklyAveragePoint


def _week_start(day: datetime.date) -> datetime.date:
    """Lunes de la semana ISO a la que pertenece `day`."""
    return day - datetime.timedelta(days=day.weekday())


def weekly_averages(metrics: list[BodyMetric]) -> list[WeeklyAveragePoint]:
    """Agrupa mediciones por semana (Lun-Dom) y devuelve la media de peso/cintura.

    Se ignoran los None al calcular la media de cada semana, pero se cuentan
    los registros válidos en `sample_count` para que la UI pueda mostrar
    "media de 3 días" en vez de dar una falsa sensación de precisión.
    """
    weights: dict[datetime.date, list[float]] = defaultdict(list)
    waists: dict[datetime.date, list[float]] = defaultdict(list)
    counts: dict[datetime.date, int] = defaultdict(int)

    for metric in metrics:
        week = _week_start(metric.date)
        counts[week] += 1
        if metric.weight_kg is not None:
            weights[week].append(metric.weight_kg)
        if metric.waist_cm is not None:
            waists[week].append(metric.waist_cm)

    weeks = sorted(counts.keys())
    return [
        WeeklyAveragePoint(
            week_start=week,
            avg_weight_kg=round(sum(weights[week]) / len(weights[week]), 2)
            if weights[week]
            else None,
            avg_waist_cm=round(sum(waists[week]) / len(waists[week]), 2) if waists[week] else None,
            sample_count=counts[week],
        )
        for week in weeks
    ]
