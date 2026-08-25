"""Automatismo semanal: Garmin -> Claude -> plan de la semana que viene.

Pensado para correr los domingos a las 20:00 (Europe/Madrid) desde GitHub
Actions. Flujo:
  1. Comprueba que "toca" ejecutar (domingo por la tarde en Madrid), salvo --force.
  2. Extrae recuperación y actividades reales de los últimos 7 días de Garmin.
  3. Le pide a Claude (vía Claude Code headless, dentro del plan Pro) el plan
     de los próximos 7 días en JSON estricto.
  4. Escribe ese plan en la BD del usuario (tabla planned_workouts), reemplazando
     la semana entrante.
  5. Si hay credenciales de Gmail configuradas, envía un informe breve por
     email (cómo fue la semana que termina + el ajuste decidido). Es un
     extra: si falla, no tumba el resto del pipeline (el plan ya se escribió).

Uso:
  python -m app.automation.weekly_plan <email>              # ejecución real
  python -m app.automation.weekly_plan <email> --force      # ignora el guard horario
  python -m app.automation.weekly_plan <email> --dry-run    # no escribe, solo imprime
  python -m app.automation.weekly_plan <email> --stub-metrics  # sin Garmin (prueba)
"""

import argparse
import datetime
import os
import sys
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.automation import coach, email_report, garmin_metrics, macro
from app.core.database import SessionLocal
from app.crud import planned as planned_crud
from app.crud import workout as workout_crud
from app.models.user import User
from app.schemas.planned import PlannedWorkoutIn, WeekPlanReplace
from app.utils.app_settings import MACRO_START_DATE_KEY, get_setting

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


def _macro_week_info(db, user_id: int, week_start: datetime.date):
    """Info de la semana del macrociclo según macro_start_date del usuario.

    Si no está fijada, trata la semana objetivo como la 1 (arranque del plan).
    """
    raw = get_setting(db, user_id, MACRO_START_DATE_KEY)
    macro_start = datetime.date.fromisoformat(raw) if raw else week_start
    n = macro.week_number_for(macro_start, week_start)
    return macro.get_week(n), n


def _prev_week_adherence(db, user_id: int, week_start: datetime.date) -> tuple[int, int]:
    """(días con entreno prescrito, sesiones completadas) de la semana que
    ACABA (la anterior a `week_start`, que es el lunes que viene)."""
    prev_start = week_start - datetime.timedelta(days=7)
    prev_end = week_start - datetime.timedelta(days=1)
    prev_planned = planned_crud.list_planned(db, user_id, prev_start, prev_end)
    planned_count = sum(1 for p in prev_planned if p.workout_type is not None)
    prev_sessions = workout_crud.list_sessions(db, user_id, start=prev_start, end=prev_end)
    completed_count = sum(1 for s in prev_sessions if s.completed)
    return planned_count, completed_count


def plan_and_write(
    email: str,
    week_start: datetime.date,
    *,
    dry_run: bool,
    stub_metrics: bool,
    gmail_address: str | None = None,
    gmail_app_password: str | None = None,
) -> int:
    """Genera el plan de `week_start` (con la semana del macrociclo que toque) y
    lo escribe. Reutilizado por el cron (semana siguiente) y el bootstrap
    (semana actual)."""
    today = datetime.datetime.now(TZ).date()

    metrics = (
        garmin_metrics.stub()
        if stub_metrics
        else garmin_metrics.collect(garmin_metrics.tokenstore_path(), today)
    )
    print(metrics.to_prompt_summary())

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == email.lower()))
        if user is None and not dry_run:
            print(f"No existe la cuenta {email}", file=sys.stderr)
            return 1

        week_info, week_num = _macro_week_info(db, user.id if user else 0, week_start)
        print(f"Semana {week_num} del macrociclo · {week_info.phase_block}")

        plan = coach.generate_plan(metrics, week_start, week_info)
        if plan.get("coach_note"):
            print(f"\nCoach: {plan['coach_note']}\n")
        for d in plan["days"]:
            print(f"  d{d['weekday']} · {d.get('workout_type') or 'descanso'} · {d['title']}")

        planned_count, completed_count = (
            _prev_week_adherence(db, user.id, week_start) if user else (0, 0)
        )
        report_body = email_report.build_report_body(
            metrics, plan, week_start, planned_count, completed_count
        )
        print(f"\n--- Informe semanal ---\n{report_body}\n")

        if dry_run:
            print("[dry-run] No se escribe nada en la BD ni se envía el email.")
            return 0

        rows = planned_crud.replace_week(db, user.id, _plan_to_week_replace(plan, week_start))
        print(f"\nPlan escrito: {len(rows)} días planificados para {email}.")

        if gmail_address and gmail_app_password:
            try:
                email_report.send_weekly_email(
                    gmail_address,
                    gmail_app_password,
                    f"CIMA — informe semanal ({week_start.isoformat()})",
                    report_body,
                )
                print("Informe semanal enviado por email.")
            except Exception as e:  # noqa: BLE001 - el email es un extra, no debe tumbar el run
                print(f"No se pudo enviar el email semanal: {e}", file=sys.stderr)
        else:
            print("GMAIL_ADDRESS/GMAIL_APP_PASSWORD no configurados: no se envía email semanal.")
    finally:
        db.close()
    return 0


def run(email: str, *, force: bool, dry_run: bool, stub_metrics: bool) -> int:
    if not force and not should_run_now():
        print("No toca ejecutar ahora (no es domingo tarde en Madrid). Saliendo sin hacer nada.")
        return 0
    week_start = next_monday(datetime.datetime.now(TZ).date())
    print(f"Planificando la semana del {week_start.isoformat()} para {email}")
    return plan_and_write(
        email,
        week_start,
        dry_run=dry_run,
        stub_metrics=stub_metrics,
        gmail_address=os.environ.get("GMAIL_ADDRESS"),
        gmail_app_password=os.environ.get("GMAIL_APP_PASSWORD"),
    )


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
