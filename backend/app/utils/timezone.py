import datetime
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def app_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().app_timezone)


def now_local() -> datetime.datetime:
    return datetime.datetime.now(app_tz())


def today_local() -> datetime.date:
    return now_local().date()
