import datetime

from sqlalchemy.orm import Session

from app.crud import body_metric as body_metric_crud
from app.crud import habit as habit_crud
from app.crud import workout as workout_crud
from app.schemas.stats import ExportPayload
from app.utils.stats import compute_monthly_stats, month_bounds


def build_export_payload(db: Session, year: int, month: int) -> ExportPayload:
    start, end = month_bounds(year, month)
    stats = compute_monthly_stats(db, year, month)

    sessions = workout_crud.list_sessions(db, start=start, end=end)
    workouts_dump = [
        {
            "date": s.date.isoformat(),
            "type": s.workout_type.value,
            "cycle_week": s.cycle_week,
            "notes": s.notes,
            "running_minutes": s.running_minutes,
            "running_feeling": s.running_feeling,
            "exercises": [
                {
                    "name": ex.name,
                    "sets": [
                        {
                            "set": st.set_number,
                            "weight_kg": st.weight_kg,
                            "reps": st.reps,
                            "rir": st.rir,
                        }
                        for st in ex.sets
                    ],
                }
                for ex in s.exercises
            ],
        }
        for s in sessions
    ]

    habits_dump = []
    for habit in habit_crud.list_habits(db):
        logs = habit_crud.list_logs_in_range(db, habit.id, start, end)
        habits_dump.append(
            {
                "habit": habit.name,
                "logs": [
                    {"date": log.date.isoformat(), "done": log.done, "value": log.value}
                    for log in logs
                ],
            }
        )

    metrics_dump = [
        {"date": m.date.isoformat(), "weight_kg": m.weight_kg, "waist_cm": m.waist_cm}
        for m in body_metric_crud.list_metrics(db, start, end)
    ]

    return ExportPayload(
        generated_at=datetime.datetime.now(datetime.UTC),
        stats=stats,
        workouts=workouts_dump,
        habits=habits_dump,
        body_metrics=metrics_dump,
    )


def render_as_text(payload: ExportPayload) -> str:
    """Resumen en texto plano, pensado para pegar directamente en un chat con un coach IA."""
    s = payload.stats
    sessions_summary = ", ".join(f"{k}: {v}" for k, v in s.sessions_by_type.items()) or "ninguna"
    lines = [
        f"RESUMEN {s.month:02d}/{s.year}",
        "=" * 30,
        f"Sesiones completadas: {s.sessions_completed} ({sessions_summary})",
        f"Media de pasos: {s.avg_steps or 'sin datos'} "
        f"(objetivo cumplido {s.steps_goal_days} días)",
        f"Peso: {s.weight_start_kg or '?'}kg -> {s.weight_end_kg or '?'}kg "
        f"(tendencia {s.weight_trend_kg or 0:+}kg)",
        f"Cintura: {s.waist_start_cm or '?'}cm -> {s.waist_end_cm or '?'}cm "
        f"(tendencia {s.waist_trend_cm or 0:+}cm)",
        f"Pausas activas: {s.breaks_done}/{s.breaks_total} hechas",
        f"Cumplimiento de hábitos: {s.habit_completion_rate * 100:.0f}%",
        f"Puntos del mes: {s.points_total} ({s.perfect_days} días perfectos ⭐)",
        "",
        "ENTRENOS:",
    ]
    for w in payload.workouts:
        lines.append(f"- {w['date']} · {w['type']} (semana {w['cycle_week']})")
        for ex in w["exercises"]:
            sets_str = " | ".join(
                f"{st['weight_kg'] or '-'}kg x{st['reps'] or '-'}" for st in ex["sets"]
            )
            lines.append(f"    {ex['name']}: {sets_str}")
        if w["running_minutes"]:
            lines.append(
                f"    Running: {w['running_minutes']} min, sensación {w['running_feeling']}/5"
            )

    lines.append("")
    lines.append("HABITOS:")
    for h in payload.habits:
        done_days = sum(1 for log in h["logs"] if log["done"])
        lines.append(f"- {h['habit']}: {done_days}/{len(h['logs'])} días cumplidos")

    return "\n".join(lines)
