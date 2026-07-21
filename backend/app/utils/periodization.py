import datetime

from sqlalchemy.orm import Session

from app.schemas.workout import PeriodizationInfo
from app.utils.app_settings import get_program_start_date

# Definición del ciclo de 4 semanas pedido en el spec:
# S1 RIR 3 -> S2 RIR 2 -> S3 RIR 1-2 (+2,5kg) -> S4 descarga (-2 series)
_CYCLE: dict[int, PeriodizationInfo] = {
    1: PeriodizationInfo(
        cycle_week=1,
        label="Semana 1",
        rir_target="RIR 3",
        weight_adjustment_kg=0,
        set_adjustment=0,
        description="Toma de contacto. Deja 3 reps en reserva en cada serie.",
    ),
    2: PeriodizationInfo(
        cycle_week=2,
        label="Semana 2",
        rir_target="RIR 2",
        weight_adjustment_kg=0,
        set_adjustment=0,
        description="Mismo peso que S1, aprieta un poco más: deja solo 2 reps en reserva.",
    ),
    3: PeriodizationInfo(
        cycle_week=3,
        label="Semana 3",
        rir_target="RIR 1-2",
        weight_adjustment_kg=2.5,
        set_adjustment=0,
        description="Semana de mayor exigencia: sube +2,5kg sobre el peso base.",
    ),
    4: PeriodizationInfo(
        cycle_week=4,
        label="Semana 4 · Descarga",
        rir_target="RIR 3-4",
        weight_adjustment_kg=0,
        set_adjustment=-2,
        description="Descarga: mismo peso que S1 pero 2 series menos por ejercicio.",
    ),
}


def compute_cycle_week(db: Session, user_id: int, on_date: datetime.date) -> int:
    start = get_program_start_date(db, user_id)
    weeks_elapsed = (on_date - start).days // 7
    return (weeks_elapsed % 4) + 1


def get_periodization_info(cycle_week: int) -> PeriodizationInfo:
    return _CYCLE[cycle_week]


def suggested_weight_kg(base_weight_kg: float | None, cycle_week: int) -> float | None:
    if base_weight_kg is None:
        return None
    return round(base_weight_kg + _CYCLE[cycle_week].weight_adjustment_kg, 2)


def suggested_sets(target_sets: int, cycle_week: int) -> int:
    return max(1, target_sets + _CYCLE[cycle_week].set_adjustment)
