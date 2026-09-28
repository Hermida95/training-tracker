import datetime
import types

from app.automation.telegram_service import (
    format_meal_message,
    format_morning_message,
    format_today_message,
    format_training_message,
)
from app.models.workout import WorkoutType
from app.schemas.today import TodayHabit, TodayMeal, TodaySummary, TodayTraining
from app.schemas.workout import PeriodizationInfo

MONDAY = datetime.date(2026, 8, 24)


def _summary(**overrides) -> TodaySummary:
    base = dict(
        date=MONDAY,
        morning_routine=[TodayHabit(habit_id=1, name="McGill Big 3", done=False)],
        meal=TodayMeal(id=1, title="Semana 1", has_file=False, text_excerpt="Lunes: pollo"),
        training=TodayTraining(
            workout_type=WorkoutType.GYM1,
            title="Gym A",
            details="Sentadilla 4x8",
            is_rest_day=False,
            source="manual",
            periodization=PeriodizationInfo(
                cycle_week=1,
                label="Semana 1",
                rir_target="RIR 3",
                weight_adjustment_kg=0,
                set_adjustment=0,
                description="Toma de contacto.",
            ),
        ),
    )
    base.update(overrides)
    return TodaySummary(**base)


# --- Formateo (funciones puras, sin red) -----------------------------------


def test_format_morning_message_lists_due_habits():
    text = format_morning_message(_summary())
    assert "Rutina de mañana" in text
    assert "⬜ McGill Big 3" in text


def test_format_morning_message_empty_when_nothing_due():
    text = format_morning_message(_summary(morning_routine=[]))
    assert "Nada programado hoy" in text


def test_format_meal_message_includes_excerpt():
    text = format_meal_message(_summary())
    assert "Semana 1" in text
    assert "Lunes: pollo" in text


def test_format_meal_message_without_menu():
    text = format_meal_message(_summary(meal=None))
    assert "Sin menú subido todavía" in text


def test_format_training_message_includes_periodization():
    text = format_training_message(_summary())
    assert "Gym A (GYM1)" in text
    assert "RIR 3" in text


def test_format_training_message_rest_day():
    rest = TodayTraining(
        workout_type=None, title="Descanso", details=None, is_rest_day=True, source=None
    )
    text = format_training_message(_summary(training=rest))
    assert "Descanso (descanso)" in text


def test_format_today_message_combines_all_sections_once():
    text = format_today_message(_summary())
    assert text.count("CIMA — hoy") == 1
    assert "Rutina de mañana" in text
    assert "Comida" in text
    assert "Entreno" in text


# --- Vinculación del chat_id -------------------------------------------------


def test_link_and_unlink_telegram_chat_id(client):
    linked = client.patch("/api/v1/users/me/telegram", json={"chat_id": "987654321"}).json()
    assert linked["telegram_chat_id"] == "987654321"
    assert client.get("/api/v1/auth/me").json()["telegram_chat_id"] == "987654321"

    unlinked = client.patch("/api/v1/users/me/telegram", json={"chat_id": None}).json()
    assert unlinked["telegram_chat_id"] is None


def test_link_telegram_rejects_non_numeric_chat_id(client):
    res = client.patch("/api/v1/users/me/telegram", json={"chat_id": "abc"})
    assert res.status_code == 422


# --- Endpoints internos de notificación (Cloud Scheduler) -------------------


def _fake_settings(**overrides):
    base = dict(telegram_bot_token="", scheduler_shared_secret="")
    base.update(overrides)
    return types.SimpleNamespace(**base)


def test_notify_endpoint_rejects_missing_or_unconfigured_secret(client):
    # Sin SCHEDULER_SHARED_SECRET configurado (default de test), fail-closed.
    assert client.post("/api/v1/internal/notify/morning").status_code == 401


def test_notify_endpoint_rejects_wrong_secret(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.endpoints.internal.get_settings",
        lambda: _fake_settings(scheduler_shared_secret="topsecret"),
    )
    res = client.post("/api/v1/internal/notify/morning", headers={"X-Scheduler-Secret": "wrong"})
    assert res.status_code == 401


def test_notify_endpoint_sends_only_to_linked_users(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.endpoints.internal.get_settings",
        lambda: _fake_settings(scheduler_shared_secret="topsecret", telegram_bot_token="bot-token"),
    )
    sent = []
    monkeypatch.setattr(
        "app.automation.telegram_service.send_message",
        lambda token, chat_id, text, sender=None: sent.append((token, chat_id, text)),
    )
    headers = {"X-Scheduler-Secret": "topsecret"}

    # Nadie vinculado todavía: no manda nada.
    res = client.post("/api/v1/internal/notify/morning", headers=headers)
    assert res.status_code == 200
    assert res.json() == {"sent": 0, "failed": 0}
    assert sent == []

    client.patch("/api/v1/users/me/telegram", json={"chat_id": "123456"})
    res2 = client.post("/api/v1/internal/notify/morning", headers=headers)
    assert res2.json() == {"sent": 1, "failed": 0}
    assert len(sent) == 1
    assert sent[0][:2] == ("bot-token", "123456")


def test_notify_endpoint_without_bot_token_sends_nothing(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.endpoints.internal.get_settings",
        lambda: _fake_settings(scheduler_shared_secret="topsecret", telegram_bot_token=""),
    )
    client.patch("/api/v1/users/me/telegram", json={"chat_id": "123456"})
    res = client.post(
        "/api/v1/internal/notify/training", headers={"X-Scheduler-Secret": "topsecret"}
    )
    assert res.json() == {"sent": 0, "failed": 0}


# --- Webhook del bot (/hoy) ---------------------------------------------------


def test_webhook_rejects_wrong_token(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.endpoints.telegram.get_settings",
        lambda: _fake_settings(telegram_bot_token="real-token"),
    )
    res = client.post("/api/v1/telegram/webhook/wrong-token", json={})
    assert res.status_code == 404


def test_webhook_hoy_command_replies_with_today_summary(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.endpoints.telegram.get_settings",
        lambda: _fake_settings(telegram_bot_token="real-token"),
    )
    client.patch("/api/v1/users/me/telegram", json={"chat_id": "42"})

    sent = []
    monkeypatch.setattr(
        "app.automation.telegram_service.send_message",
        lambda token, chat_id, text, sender=None: sent.append((token, chat_id, text)),
    )

    update = {"message": {"chat": {"id": 42}, "text": "/hoy"}}
    res = client.post("/api/v1/telegram/webhook/real-token", json=update)
    assert res.status_code == 200
    assert len(sent) == 1
    assert sent[0][:2] == ("real-token", "42")
    assert "CIMA — hoy" in sent[0][2]


def test_webhook_ignores_unlinked_chats_gracefully(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.endpoints.telegram.get_settings",
        lambda: _fake_settings(telegram_bot_token="real-token"),
    )
    sent = []
    monkeypatch.setattr(
        "app.automation.telegram_service.send_message",
        lambda token, chat_id, text, sender=None: sent.append((token, chat_id, text)),
    )

    update = {"message": {"chat": {"id": 999}, "text": "/hoy"}}
    res = client.post("/api/v1/telegram/webhook/real-token", json=update)
    assert res.status_code == 200
    assert "no está vinculado" in sent[0][2]
