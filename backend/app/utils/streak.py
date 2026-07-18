import datetime

from sqlalchemy.orm import Session

from app.models.habit import Habit, HabitLog


def compute_streak(db: Session, habit: Habit, as_of: datetime.date) -> int:
    """Cuenta días consecutivos de cumplimiento hacia atrás desde `as_of`.

    Solo cuentan los días en los que el hábito estaba "due" (según active_days).
    Un día debido y no cumplido rompe la racha. Un día no debido se salta sin
    afectar la racha (ej. McGill Big 3 es L/X/V: el martes no cuenta ni rompe).
    Un hábito debido *hoy* pero aún no registrado no rompe la racha todavía
    (se considera "pendiente", no "fallado") — por eso empezamos en `as_of`
    y si hoy no hay log lo saltamos sin cortar, pero solo para el propio `as_of`.
    """
    logs_by_date = {
        log.date: log
        for log in db.query(HabitLog)
        .filter(HabitLog.habit_id == habit.id, HabitLog.date <= as_of)
        .all()
    }

    streak = 0
    day = as_of
    # Máximo un año hacia atrás para evitar bucles infinitos si active_days está vacío.
    for _ in range(366):
        if not habit.is_due_on(day):
            day -= datetime.timedelta(days=1)
            continue

        log = logs_by_date.get(day)
        if log is None:
            if day == as_of:
                # Hoy todavía no se ha marcado: no rompe la racha, simplemente no suma.
                day -= datetime.timedelta(days=1)
                continue
            break

        if not log.done:
            break

        streak += 1
        day -= datetime.timedelta(days=1)

    return streak
