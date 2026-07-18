import datetime

from pydantic import BaseModel, ConfigDict


class BodyMetricUpsert(BaseModel):
    date: datetime.date
    weight_kg: float | None = None
    waist_cm: float | None = None


class BodyMetricRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: datetime.date
    weight_kg: float | None = None
    waist_cm: float | None = None


class WeeklyAveragePoint(BaseModel):
    week_start: datetime.date
    avg_weight_kg: float | None = None
    avg_waist_cm: float | None = None
    sample_count: int
