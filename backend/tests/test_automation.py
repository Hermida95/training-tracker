import datetime
import json
from zoneinfo import ZoneInfo

import pytest

from app.automation import coach, macro, weekly_plan
from app.automation.garmin_metrics import stub

MADRID = ZoneInfo("Europe/Madrid")


def _valid_plan() -> dict:
    return {
        "days": [
            {"weekday": i, "workout_type": t, "title": f"Día {i}", "details": "x"}
            for i, t in enumerate(["GYM1", "RUNNING", "GYM2", "RUNNING", "GYM3", "RUNNING", None])
        ],
        "coach_note": "semana normal",
    }


# --- Guard horario y cálculo de semana ---


def test_should_run_only_sunday_evening():
    assert weekly_plan.should_run_now(datetime.datetime(2026, 8, 30, 20, 0, tzinfo=MADRID))  # dom
    assert not weekly_plan.should_run_now(datetime.datetime(2026, 8, 30, 12, 0, tzinfo=MADRID))
    assert not weekly_plan.should_run_now(
        datetime.datetime(2026, 8, 31, 20, 0, tzinfo=MADRID)
    )  # lun


def test_should_run_handles_dst_via_utc_trigger():
    # 18:00 UTC en verano (CEST) son las 20:00 en Madrid -> debe ejecutar
    summer = datetime.datetime(2026, 8, 30, 18, 0, tzinfo=ZoneInfo("UTC"))
    assert weekly_plan.should_run_now(summer)
    # 18:00 UTC en invierno (CET) son las 19:00 en Madrid -> también entra en la ventana
    winter = datetime.datetime(2026, 12, 27, 19, 0, tzinfo=ZoneInfo("UTC"))
    assert weekly_plan.should_run_now(winter)


def test_next_monday():
    # sábado 29 ago 2026 -> lunes 31
    assert weekly_plan.next_monday(datetime.date(2026, 8, 29)) == datetime.date(2026, 8, 31)
    # domingo 30 ago -> lunes 31
    assert weekly_plan.next_monday(datetime.date(2026, 8, 30)) == datetime.date(2026, 8, 31)
    # lunes 31 -> lunes siguiente 7 sep
    assert weekly_plan.next_monday(datetime.date(2026, 8, 31)) == datetime.date(2026, 9, 7)


def test_plan_maps_weekdays_to_dates():
    week = weekly_plan._plan_to_week_replace(_valid_plan(), datetime.date(2026, 8, 31))
    assert week.week_start == datetime.date(2026, 8, 31)
    assert week.days[0].date == datetime.date(2026, 8, 31)  # lunes
    assert week.days[6].date == datetime.date(2026, 9, 6)  # domingo
    assert week.days[6].workout_type is None
    assert all(d.source == "ai" for d in week.days)


# --- Macrociclo ---


def test_macro_week_number_and_lookup():
    start = datetime.date(2026, 8, 24)  # lunes semana 1
    assert macro.week_number_for(start, datetime.date(2026, 8, 24)) == 1
    assert macro.week_number_for(start, datetime.date(2026, 8, 31)) == 2
    # semana 4 es descarga
    assert macro.get_week(4).deload is True
    # semanas 1-3 llevan tope de FC 148
    assert macro.get_week(1).fc_cap == "148 ppm"
    assert macro.get_week(5).fc_cap is None
    # clamp fuera de rango
    assert macro.get_week(99).week == 26


def test_macro_week_info_injected_in_prompt():
    week = macro.get_week(1)
    prompt = coach._build_prompt(stub(), datetime.date(2026, 8, 24), week)
    assert "Semana 1 del macrociclo" in prompt
    assert "148 ppm" in prompt


# --- Coach: validación y reintento con runner inyectado ---


def test_generate_plan_accepts_valid_json():
    plan = coach.generate_plan(
        stub(), datetime.date(2026, 8, 31), runner=lambda _: json.dumps(_valid_plan())
    )
    assert len(plan["days"]) == 7


def test_generate_plan_tolerates_markdown_fences():
    fenced = "```json\n" + json.dumps(_valid_plan()) + "\n```"
    plan = coach.generate_plan(stub(), datetime.date(2026, 8, 31), runner=lambda _: fenced)
    assert plan["days"][0]["workout_type"] == "GYM1"


def test_generate_plan_retries_then_succeeds():
    calls = {"n": 0}

    def flaky(_prompt):
        calls["n"] += 1
        return "no soy json" if calls["n"] == 1 else json.dumps(_valid_plan())

    plan = coach.generate_plan(stub(), datetime.date(2026, 8, 31), runner=flaky)
    assert calls["n"] == 2 and len(plan["days"]) == 7


def test_generate_plan_rejects_wrong_day_count():
    bad = {"days": _valid_plan()["days"][:5]}
    with pytest.raises(RuntimeError):
        coach.generate_plan(stub(), datetime.date(2026, 8, 31), runner=lambda _: json.dumps(bad))


def test_generate_plan_rejects_invalid_type():
    bad = _valid_plan()
    bad["days"][0]["workout_type"] = "PILATES"
    with pytest.raises(RuntimeError):
        coach.generate_plan(stub(), datetime.date(2026, 8, 31), runner=lambda _: json.dumps(bad))
