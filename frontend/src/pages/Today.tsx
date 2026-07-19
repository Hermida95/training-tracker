import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { habitsApi } from "../api/habits";
import { workoutsApi } from "../api/workouts";
import {
  CheckIcon,
  CircleCheckIcon,
  CircleHalfIcon,
  CircleIcon,
  FlameIcon,
  LeafIcon,
  StarIcon,
} from "../components/icons";
import { Stepper } from "../components/Stepper";
import type { DayScore, DayScoreTier, HabitWithStatus, PeriodizationInfo } from "../types";
import { todayIsoMadrid as todayIso } from "../utils/date";

// Icono y texto por nivel de puntuación del día. El "plus" grande es el día
// perfecto (100% -> 3 pts); un día decente (>=75%) mantiene la racha viva.
const TIER_DISPLAY: Record<DayScoreTier, { icon: ReactNode; label: string }> = {
  perfect: { icon: <StarIcon size={26} />, label: "Día perfecto · +3 pts" },
  great: { icon: <CircleCheckIcon size={26} />, label: "Buen día · +2 pts" },
  half: { icon: <CircleHalfIcon size={26} />, label: "A medias · +1 pt" },
  missed: { icon: <CircleIcon size={26} />, label: "Aún sin puntos hoy" },
  rest: { icon: <LeafIcon size={26} />, label: "Día libre" },
};

// Paso del stepper proporcional al objetivo del hábito, para que registrar
// sea rápido con cualquier escala: 2L de agua -> 0.25, 60 min de estudio -> 5,
// 10.000 pasos -> 500. Sin objetivo definido, incrementos de 1.
function stepFor(habit: HabitWithStatus): number {
  const target = habit.target_value;
  if (target === null) return 1;
  if (target <= 3) return 0.25;
  if (target <= 12) return 0.5;
  if (target <= 300) return 5;
  return 500;
}

export default function Today() {
  const [habits, setHabits] = useState<HabitWithStatus[]>([]);
  const [periodization, setPeriodization] = useState<PeriodizationInfo | null>(null);
  const [score, setScore] = useState<DayScore | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    Promise.all([
      habitsApi.today(todayIso()),
      workoutsApi.periodization(todayIso()),
      habitsApi.score(todayIso()),
    ])
      .then(([h, p, s]) => {
        setHabits(h);
        setPeriodization(p);
        setScore(s);
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

        {score && score.tier !== "rest" && (
          <div className={`score-card tier-${score.tier}`}>
            <span className="score-icon">{TIER_DISPLAY[score.tier].icon}</span>
            <div className="score-info">
              <strong>{TIER_DISPLAY[score.tier].label}</strong>
              <span>
                <FlameIcon /> Racha: {score.streak} {score.streak === 1 ? "día" : "días"}
                {score.tier !== "perfect" &&
                  score.due_count > 0 &&
                  ` · ${score.done_count}/${score.due_count} para el pleno`}
              </span>
            </div>
            <div
              className="score-progress"
              role="progressbar"
              aria-valuenow={Math.round((score.completion_rate ?? 0) * 100)}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <div
                className="score-progress-fill"
                style={{ width: `${(score.completion_rate ?? 0) * 100}%` }}
              />
            </div>
          </div>
        )}

        <div className="card">
          <h2>Checklist</h2>
          {loading && <p>Cargando…</p>}
          {!loading && dueHabits.length === 0 && (
            <p className="empty-state">Nada programado hoy. Descansa.</p>
          )}
          {dueHabits.map((habit) => (
            <div className="habit-row" key={habit.id}>
              <div className="info">
                <span>{habit.name}</span>
                <span className="streak">
                  <FlameIcon size={12} /> racha de {habit.current_streak}{" "}
                  {habit.current_streak === 1 ? "día" : "días"}
                </span>
              </div>

              {habit.value_type === "numeric" ? (
                <div style={{ width: 150 }}>
                  <Stepper
                    value={habit.value_today}
                    step={stepFor(habit)}
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
                  {habit.done_today ? <CheckIcon /> : null}
                </button>
              )}
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
