import datetime

from fastapi import APIRouter, HTTPException

from app.core.deps import DbSession
from app.crud import body_metric as crud
from app.schemas.body_metric import BodyMetricRead, BodyMetricUpsert, WeeklyAveragePoint
from app.utils.moving_average import weekly_averages

router = APIRouter(prefix="/body-metrics", tags=["body-metrics"])


@router.get("", response_model=list[BodyMetricRead])
def list_metrics(
    db: DbSession, start: datetime.date | None = None, end: datetime.date | None = None
):
    return crud.list_metrics(db, start, end)


@router.post("", response_model=BodyMetricRead, status_code=201)
def upsert_metric(data: BodyMetricUpsert, db: DbSession):
    return crud.upsert_metric(db, data)


@router.get("/weekly-average", response_model=list[WeeklyAveragePoint])
def get_weekly_average(
    db: DbSession, start: datetime.date | None = None, end: datetime.date | None = None
):
    """Media móvil semanal (Lun-Dom) de peso y cintura, para graficar tendencia."""
    metrics = crud.list_metrics(db, start, end)
    return weekly_averages(metrics)


@router.delete("/{metric_id}", status_code=204)
def delete_metric(metric_id: int, db: DbSession):
    metric = crud.get_metric(db, metric_id)
    if not metric:
        raise HTTPException(404, "Medición no encontrada")
    crud.delete_metric(db, metric)
