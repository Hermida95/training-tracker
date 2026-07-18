from fastapi import APIRouter

from app.core.deps import DbSession
from app.schemas.stats import MonthlyStats
from app.utils.stats import compute_monthly_stats
from app.utils.timezone import today_local

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/monthly", response_model=MonthlyStats)
def monthly_stats(db: DbSession, year: int | None = None, month: int | None = None):
    today = today_local()
    return compute_monthly_stats(db, year or today.year, month or today.month)
