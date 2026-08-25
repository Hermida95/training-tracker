"""Arranque del plan maestro de 6 meses para una cuenta.

Hace, una sola vez, lo que el cron semanal hará luego solo:
  1. Fija la fecha de inicio del macrociclo (lunes de la semana 1) en app_settings.
  2. Genera y carga el plan de la SEMANA ACTUAL (para que "Hoy toca" funcione ya),
     usando el mismo pipeline Garmin+Claude que el cron.
  3. (Opcional) carga un menú semanal como documento de la pestaña Menú.

A partir de aquí, cada domingo el cron genera la semana SIGUIENTE del macrociclo.

Uso:
  DATABASE_URL=... GARMINTOKENS=... \
    python -m app.automation.bootstrap_macro <email> --macro-start 2026-08-24 [--menu <fichero.md>]
  # --stub-metrics para probar sin Garmin
"""

import argparse
import datetime
import sys
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.automation import weekly_plan
from app.core.database import SessionLocal
from app.models.menu import MenuDocument
from app.models.user import User
from app.utils.app_settings import MACRO_START_DATE_KEY, set_setting

TZ = ZoneInfo("Europe/Madrid")


def _current_monday() -> datetime.date:
    today = datetime.datetime.now(TZ).date()
    return today - datetime.timedelta(days=today.weekday())


def load_menu(db, user_id: int, title: str, text: str) -> None:
    """Carga (o reemplaza por título) un menú de texto en la pestaña Menú."""
    existing = db.scalar(
        select(MenuDocument).where(MenuDocument.user_id == user_id, MenuDocument.title == title)
    )
    if existing:
        existing.text_content = text
    else:
        db.add(MenuDocument(user_id=user_id, title=title, text_content=text, file_size=0))
    db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Arranca el plan maestro de 6 meses.")
    parser.add_argument("email")
    parser.add_argument("--macro-start", required=True, help="Lunes de la semana 1 (YYYY-MM-DD)")
    parser.add_argument("--menu", help="Ruta a un .md con el menú semanal (se carga en Menú)")
    parser.add_argument("--stub-metrics", action="store_true")
    args = parser.parse_args()

    macro_start = datetime.date.fromisoformat(args.macro_start)
    if macro_start.weekday() != 0:
        print("El inicio del macrociclo debe ser un lunes.", file=sys.stderr)
        raise SystemExit(1)

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == args.email.lower()))
        if user is None:
            print(f"No existe la cuenta {args.email}", file=sys.stderr)
            raise SystemExit(1)
        set_setting(db, user.id, MACRO_START_DATE_KEY, macro_start.isoformat())
        print(f"macro_start_date fijado a {macro_start.isoformat()} para {args.email}")

        if args.menu:
            text = open(args.menu, encoding="utf-8").read()
            title = "Menú semanal · déficit 82 kg"
            load_menu(db, user.id, title, text)
            print(f"Menú cargado en la pestaña Menú ({len(text)} caracteres).")
    finally:
        db.close()

    # Carga la semana en curso con el pipeline real (Garmin + Claude).
    print("\n--- Generando el plan de la semana actual ---")
    rc = weekly_plan.plan_and_write(
        args.email, _current_monday(), dry_run=False, stub_metrics=args.stub_metrics
    )
    raise SystemExit(rc)


if __name__ == "__main__":
    main()
