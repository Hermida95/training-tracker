import datetime
import json
from zoneinfo import ZoneInfo

import pytest

from app.automation import coach, macro, weekly_plan
from app.automation.garmin_metrics import WeeklyMetrics, _parse_activity, stub

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


# --- Actividades reales de Garmin (planificado vs. real) ---


def test_parse_activity_extracts_known_fields():
    raw = {
        "activityType": {"typeKey": "running"},
        "activityName": "Rodaje mañanero",
        "startTimeLocal": "2026-08-18 07:15:00",
        "duration": 2520,  # 42 min
        "distance": 8100,  # 8.1 km
        "averageHR": 148,
        "elevationGain": 65,
    }
    activity = _parse_activity(raw)
    assert activity.date == "2026-08-18"
    assert activity.activity_type == "running"
    assert activity.duration_min == 42
    assert activity.distance_km == 8.1
    assert activity.avg_hr == 148
    assert activity.pace_min_km == 5.19  # round(42 / 8.1, 2)
    assert activity.elevation_gain_m == 65


def test_parse_activity_skips_pace_without_real_distance():
    # Sesión de gym: tiene duración pero no desplazamiento -> sin ritmo.
    raw = {
        "activityType": {"typeKey": "strength_training"},
        "startTimeLocal": "2026-08-19 18:00:00",
        "duration": 3300,
        "distance": 0,
    }
    activity = _parse_activity(raw)
    assert activity.distance_km == 0
    assert activity.pace_min_km is None


def test_parse_activity_returns_none_without_activity_type():
    assert _parse_activity({"startTimeLocal": "2026-08-18 07:15:00"}) is None


def test_prompt_summary_includes_real_activities():
    summary = stub().to_prompt_summary()
    assert "Actividades reales registradas" in summary
    assert "running" in summary
    assert "5:00/km" in summary  # 40 min / 8.0 km


def test_prompt_summary_placeholder_when_no_activities():
    summary = WeeklyMetrics().to_prompt_summary()
    assert "(sin actividades registradas esta semana)" in summary
