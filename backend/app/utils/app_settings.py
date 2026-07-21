import datetime

from sqlalchemy.orm import Session

from app.models.app_setting import AppSetting

PROGRAM_START_DATE_KEY = "program_start_date"
BREAK_INTERVAL_KEY = "break_interval_minutes"
BREAK_WINDOW_START_KEY = "break_window_start"
BREAK_WINDOW_END_KEY = "break_window_end"


def get_setting(db: Session, user_id: int, key: str, default: str | None = None) -> str | None:
    row = db.get(AppSetting, (user_id, key))
    return row.value if row else default


def set_setting(db: Session, user_id: int, key: str, value: str) -> None:
    row = db.get(AppSetting, (user_id, key))
    if row is None:
        db.add(AppSetting(user_id=user_id, key=key, value=value))
    else:
        row.value = value
    db.commit()


def get_program_start_date(db: Session, user_id: int) -> datetime.date:
    """Fecha de inicio del ciclo de periodización de 4 semanas (por usuario).

    Si nunca se ha fijado explícitamente, se siembra en el primer acceso con
    el lunes de la semana actual, para que el ciclo empiece en semana 1 "hoy".
    """
    raw = get_setting(db, user_id, PROGRAM_START_DATE_KEY)
    if raw:
        return datetime.date.fromisoformat(raw)

    monday_this_week = datetime.date.today() - datetime.timedelta(
        days=datetime.date.today().weekday()
    )
    set_setting(db, user_id, PROGRAM_START_DATE_KEY, monday_this_week.isoformat())
    return monday_this_week
