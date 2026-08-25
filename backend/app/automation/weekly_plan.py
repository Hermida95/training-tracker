"""Automatismo semanal: Garmin -> Claude -> plan de la semana que viene.

Pensado para correr los domingos a las 20:00 (Europe/Madrid) desde GitHub
Actions. Flujo:
  1. Comprueba que "toca" ejecutar (domingo por la tarde en Madrid), salvo --force.
  2. Extrae métricas de recuperación de los últimos 7 días de Garmin.
  3. Le pide a Claude (vía Claude Code headless, dentro del plan Pro) el plan
     de los próximos 7 días en JSON estricto.
  4. Escribe ese plan en la BD del usuario (tabla planned_workouts), reemplazando
     la semana entrante.

Uso:
  python -m app.automation.weekly_plan <email>              # ejecución real
  python -m app.automation.weekly_plan <email> --force      # ignora el guard horario
  python -m app.automation.weekly_plan <email> --dry-run    # no escribe, solo imprime
  python -m app.automation.weekly_plan <email> --stub-metrics  # sin Garmin (prueba)
"""

import argparse
import datetime
import sys
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.automation import coach, garmin_metrics
from app.core.database import SessionLocal
from app.crud import planned as planned_crud
from app.models.user import User
from app.schemas.planned import PlannedWorkoutIn, WeekPlanReplace

TZ = ZoneInfo("Europe/Madrid")


def should_run_now(now: datetime.datetime | None = None) -> bool:
    """True si es domingo por la tarde-noche en Madrid (ventana 19:00-21:59).

    El cron de GitHub Actions va en UTC y no ajusta el horario de verano, así
    que lo disparamos a dos horas UTC candidatas y dejamos que solo la correcta
    (según la hora local real) siga adelante.
    """
    now = now or datetime.datetime.now(TZ)
    now = now.astimezone(TZ)
    return now.weekday() == 6 and 19 <= now.hour < 22


def next_monday(today: datetime.date) -> datetime.date:
    """Lunes de la semana que viene (si hoy es domingo, mañana)."""
    return today + datetime.timedelta(days=(7 - today.weekday()) % 7 or 7)


def _plan_to_week_replace(plan: dict, week_start: datetime.date) -> WeekPlanReplace:
    days = []
    for d in plan["days"]:
        date = week_start + datetime.timedelta(days=d["weekday"])
        days.append(
            PlannedWorkoutIn(
                date=date,
                workout_type=d.get("workout_type"),
                title=d["title"][:120],
                details=(d.get("details") or None),
                source="ai",
            )
        )
    return WeekPlanReplace(week_start=week_start, days=days, source="ai")


def run(email: str, *, force: bool, dry_run: bool, stub_metrics: bool) -> int:
    if not force and not should_run_now():
        print("No toca ejecutar ahora (no es domingo tarde en Madrid). Saliendo sin hacer nada.")
        return 0

    today = datetime.datetime.now(TZ).date()
    week_start = next_monday(today)
    print(f"Planificando la semana del {week_start.isoformat()} para {email}")

    # 1) Métricas
    if stub_metrics:
        metrics = garmin_metrics.stub()
    else:
        metrics = garmin_metrics.collect(garmin_metrics.tokenstore_path(), today)
    print(metrics.to_prompt_summary())

    # 2) Plan con Claude
    plan = coach.generate_plan(metrics, week_start)
    if plan.get("coach_note"):
        print(f"\nCoach: {plan['coach_note']}\n")
    for d in plan["days"]:
        print(f"  d{d['weekday']} · {d.get('workout_type') or 'descanso'} · {d['title']}")

    # 3) Escribir
    week = _plan_to_week_replace(plan, week_start)
    if dry_run:
        print("\n[dry-run] No se escribe nada en la BD.")
        return 0

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == email.lower()))
        if user is None:
            print(f"No existe la cuenta {email}", file=sys.stderr)
            return 1
        rows = planned_crud.replace_week(db, user.id, week)
        print(f"\nPlan escrito: {len(rows)} días planificados para {email}.")
    finally:
        db.close()
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera el plan semanal (Garmin + Claude).")
    parser.add_argument("email")
    parser.add_argument("--force", action="store_true", help="Ignora el guard horario")
    parser.add_argument("--dry-run", action="store_true", help="No escribe en la BD")
    parser.add_argument(
        "--stub-metrics", action="store_true", help="Métricas de ejemplo, sin Garmin"
    )
    args = parser.parse_args()
    raise SystemExit(
        run(args.email, force=args.force, dry_run=args.dry_run, stub_metrics=args.stub_metrics)
    )


if __name__ == "__main__":
    main()
