import { useEffect, useState } from "react";
import { habitsApi } from "../api/habits";
import { workoutsApi } from "../api/workouts";
import { Stepper } from "../components/Stepper";
import type { HabitWithStatus, PeriodizationInfo } from "../types";
import { todayIsoMadrid as todayIso } from "../utils/date";

export default function Today() {
  const [habits, setHabits] = useState<HabitWithStatus[]>([]);
  const [periodization, setPeriodization] = useState<PeriodizationInfo | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    Promise.all([habitsApi.today(todayIso()), workoutsApi.periodization(todayIso())])
      .then(([h, p]) => {
        setHabits(h);
        setPeriodization(p);
      })
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const toggleDone = async (habit: HabitWithStatus) => {
    await habitsApi.upsertLog(habit.id, todayIso(), !habit.done_today);
    load();
  };

  const setNumericValue = async (habit: HabitWithStatus, value: number) => {
    await habitsApi.upsertLog(habit.id, todayIso(), false, value);
    load();
  };

  const dueHabits = habits.filter((h) => h.due_today);
  const doneCount = dueHabits.filter((h) => h.done_today).length;

  return (
    <div>
      <div className="top-bar">
        <h1>Hoy</h1>
        <span className="pill ok">
          {doneCount}/{dueHabits.length}
        </span>
      </div>
      <main>
        {periodization && (
          <div className="banner">
            <strong>{periodization.label}</strong> · {periodization.rir_target}
            <p style={{ color: "inherit", opacity: 0.85, margin: "4px 0 0" }}>
              {periodization.description}
            </p>
          </div>
        )}

        <div className="card">
          <h2>Checklist</h2>
          {loading && <p>Cargando…</p>}
          {!loading && dueHabits.length === 0 && (
            <p className="empty-state">Nada programado hoy. Descansa 🙌</p>
          )}
          {dueHabits.map((habit) => (
            <div className="habit-row" key={habit.id}>
              <div className="info">
                <span>{habit.name}</span>
                <span className="streak">
                  🔥 racha de {habit.current_streak} {habit.current_streak === 1 ? "día" : "días"}
                </span>
              </div>

              {habit.value_type === "numeric" ? (
                <div style={{ width: 150 }}>
                  <Stepper
                    value={habit.value_today}
                    step={habit.unit === "L" ? 0.25 : 500}
                    onChange={(v) => setNumericValue(habit, v)}
                    suffix={habit.unit ? ` ${habit.unit}` : ""}
                  />
                </div>
              ) : (
                <button
                  className={`check-btn ${habit.done_today ? "done" : ""}`}
                  onClick={() => toggleDone(habit)}
                  aria-label={habit.done_today ? "Marcar como pendiente" : "Marcar como hecho"}
                >
                  {habit.done_today ? "✓" : ""}
                </button>
              )}
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
