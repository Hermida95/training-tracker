import { useEffect, useRef, useState } from "react";
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

  // Un timer por hábito: los toques rápidos del stepper (+/-) se agrupan en
  // una sola escritura en vez de una petición por toque.
  const pending = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());

  /** Pinta el cambio al instante y sincroniza con la API en segundo plano.
   *
   *  Sin esto, cada toque esperaba al servidor (escritura + recarga de tres
   *  endpoints) antes de pintar: eso es lo que se notaba como lentitud.
   *  `mutate` recibe el estado MÁS RECIENTE del hábito y devuelve el nuevo,
   *  para que varios toques seguidos se acumulen en vez de pisarse entre sí. */
  const updateHabit = (
    habitId: number,
    mutate: (habit: HabitWithStatus) => { done: boolean; value: number | null }
  ) => {
    let next: { done: boolean; value: number | null } | null = null;

    setHabits((prev) =>
      prev.map((h) => {
        if (h.id !== habitId) return h;
        next = mutate(h);
        return { ...h, done_today: next.done, value_today: next.value };
      })
    );

    const existing = pending.current.get(habitId);
    if (existing) clearTimeout(existing);
    pending.current.set(
      habitId,
      setTimeout(async () => {
        pending.current.delete(habitId);
        if (!next) return;
        try {
          await habitsApi.upsertLog(habitId, todayIso(), next.done, next.value);
        } finally {
          // Recarga para traer los datos derivados (rachas, puntos del día);
          // si la escritura falló, además devuelve la UI al estado real.
          load();
        }
      }, 400)
    );
  };

  const toggleDone = (habit: HabitWithStatus) =>
    updateHabit(habit.id, (h) => ({ done: !h.done_today, value: h.value_today }));

  const setNumericValue = (habit: HabitWithStatus, value: number) => {
    // El Stepper calcula el valor sobre la propiedad que tenía al pintarse, que
    // puede haber quedado atrás con toques rápidos; lo convertimos en un
    // incremento y lo aplicamos sobre el valor vigente.
    const delta = value - (habit.value_today ?? 0);
    updateHabit(habit.id, (h) => {
      const nextValue = Math.max(0, Math.round(((h.value_today ?? 0) + delta) * 100) / 100);
      // Espeja la regla del backend: un hábito numérico se da por hecho al
      // alcanzar su objetivo, para que el check se pinte en el mismo toque.
      const done = h.target_value !== null ? nextValue >= h.target_value : h.done_today;
      return { done, value: nextValue };
    });
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
                <div className="habit-stepper">
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
