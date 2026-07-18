import datetime

from pydantic import BaseModel, ConfigDict

from app.models.break_event import BreakStatus


class BreakEventCreate(BaseModel):
    scheduled_for: datetime.datetime


class BreakEventRespond(BaseModel):
    status: BreakStatus


class BreakEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scheduled_for: datetime.datetime
    status: BreakStatus
    responded_at: datetime.datetime | None = None
    postponed_from_id: int | None = None


class BreakConfig(BaseModel):
    interval_minutes: int
    window_start: str
    window_end: str
    active_weekdays: list[int] = [0, 1, 2, 3, 4]
    timezone: str
    daily_target: int = 8
