import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.body_metric import BodyMetric
from app.schemas.body_metric import BodyMetricUpsert


def list_metrics(
    db: Session,
    user_id: int,
    start: datetime.date | None = None,
    end: datetime.date | None = None,
) -> list[BodyMetric]:
    stmt = select(BodyMetric).where(BodyMetric.user_id == user_id).order_by(BodyMetric.date)
    if start:
        stmt = stmt.where(BodyMetric.date >= start)
    if end:
        stmt = stmt.where(BodyMetric.date <= end)
    return list(db.scalars(stmt))


def get_by_date(db: Session, user_id: int, date: datetime.date) -> BodyMetric | None:
    return db.scalar(
        select(BodyMetric).where(BodyMetric.user_id == user_id, BodyMetric.date == date)
    )


def get_metric(db: Session, user_id: int, metric_id: int) -> BodyMetric | None:
    metric = db.get(BodyMetric, metric_id)
    return metric if metric is not None and metric.user_id == user_id else None


def upsert_metric(db: Session, user_id: int, data: BodyMetricUpsert) -> BodyMetric:
    metric = get_by_date(db, user_id, data.date)
    if metric is None:
        metric = BodyMetric(
            user_id=user_id, date=data.date, weight_kg=data.weight_kg, waist_cm=data.waist_cm
        )
        db.add(metric)
    else:
        if data.weight_kg is not None:
            metric.weight_kg = data.weight_kg
        if data.waist_cm is not None:
            metric.waist_cm = data.waist_cm
    db.commit()
    db.refresh(metric)
    return metric


def delete_metric(db: Session, metric: BodyMetric) -> None:
    db.delete(metric)
    db.commit()
