import { useCallback, useEffect, useRef, useState } from "react";
import { habitsApi } from "../api/habits";
import { plannedApi } from "../api/planned";
import { workoutsApi } from "../api/workouts";
import {
  BarbellIcon,
  CheckIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  FlameIcon,
  LeafIcon,
  SunIcon,
} from "../components/icons";
import { Stepper } from "../components/Stepper";
import { WeekPlan } from "../components/WeekPlan";
import type {
  DayScore,
  DayScoreTier,
  HabitWithStatus,
  PeriodizationInfo,
  PlannedWorkout,
  RunningStats,
} from "../types";
import {
  addDaysIso,
  friendlyDateLabel,
  isFutureIso,
  todayIsoMadrid,
  weekdayInitial,
} from "../utils/date";

const TIER_LABEL: Record<DayScoreTier, string> = {
  perfect: "Día perfecto",
  great: "Buen día",
  half: "A medias",
  missed: "Sin completar",
  rest: "Día libre",
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

// Sin decimales de sobra: 42 km en vez de 42.0, pero conserva 42.5 si aplica.
function formatKm(km: number): string {
  return Math.round(km * 10) / 10 === Math.round(km) ? String(Math.round(km)) : km.toFixed(1);
}

export default function Today() {
  const [date, setDate] = useState(todayIsoMadrid());
  const [habits, setHabits] = useState<HabitWithStatus[]>([]);
  const [periodization, setPeriodization] = useState<PeriodizationInfo | null>(null);
  const [score, setScore] = useState<DayScore | null>(null);
  const [week, setWeek] = useState<DayScore[]>([]);
  const [planned, setPlanned] = useState<PlannedWorkout | null>(null);
  const [runningStats, setRunningStats] = useState<RunningStats | null>(null);
  const [loading, setLoading] = useState(true);

  const isToday = date === todayIsoMadrid();

  const load = useCallback(() => {
    Promise.all([
      habitsApi.today(date),
      workoutsApi.periodization(date),
      habitsApi.score(date),
      habitsApi.scoreHistory(date, 7),
      plannedApi.today(date).catch(() => null),
    ])
      .then(([h, p, s, w, pl]) => {
        setHabits(h);
        setPeriodization(p);
        setScore(s);
        setWeek(w);
        setPlanned(pl);
      })
      .finally(() => setLoading(false));
  }, [date]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  // Métrica motivadora: km del mes/año, independiente del día seleccionado.
  // Se recarga en cada montaje de la página (p.ej. al volver de marcar un rodaje).
  useEffect(() => {
    workoutsApi.runningStats().then(setRunningStats);
  }, []);

  // Un timer por hábito: los toques rápidos del stepper (+/-) se agrupan en
  // una sola escritura en vez de una petición por toque.
  const pending = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());

  /** Pinta el cambio al instante y sincroniza con la API en segundo plano.
   *  `mutate` recibe el estado MÁS RECIENTE del hábito para que varios toques
   *  seguidos se acumulen en vez de pisarse entre sí. Escribe siempre en la
   *  fecha seleccionada, que puede ser un día pasado. */
  const updateHabit = (
    habitId: number,
    mutate: (habit: HabitWithStatus) => { done: boolean; value: number | null }
  ) => {
    const writeDate = date;
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
          await habitsApi.upsertLog(habitId, writeDate, next.done, next.value);
        } finally {
          // Solo recargamos los datos derivados si seguimos en la misma fecha
          // (evita pisar la UI si el usuario ya navegó a otro día).
          if (writeDate === date) load();
        }
      }, 400)
    );
  };

  const toggleDone = (habit: HabitWithStatus) =>
    updateHabit(habit.id, (h) => ({ done: !h.done_today, value: h.value_today }));

  const setNumericValue = (habit: HabitWithStatus, value: number) => {
    const delta = value - (habit.value_today ?? 0);
    updateHabit(habit.id, (h) => {
      const nextValue = Math.max(0, Math.round(((h.value_today ?? 0) + delta) * 100) / 100);
      const done = h.target_value !== null ? nextValue >= h.target_value : h.done_today;
      return { done, value: nextValue };
    });
  };

  const dueHabits = habits.filter((h) => h.due_today);
  const doneCount = dueHabits.filter((h) => h.done_today).length;
  const completion = score?.completion_rate ?? 0;

  return (
    <div>
      <div className="top-bar date-nav">
        <button
          className="ghost icon-btn"
          onClick={() => setDate(addDaysIso(date, -1))}
          aria-label="Día anterior"
        >
          <ChevronLeftIcon />
        </button>
        <button className="date-label" onClick={() => setDate(todayIsoMadrid())}>
          {friendlyDateLabel(date)}
        </button>
        <button
          className="ghost icon-btn"
          onClick={() => setDate(addDaysIso(date, 1))}
          disabled={isFutureIso(addDaysIso(date, 1))}
          aria-label="Día siguiente"
        >
          <ChevronRightIcon />
        </button>
      </div>

      <main>
        {/* --- Héroe: completado del día entre corchetes + franja de specs --- */}
        <div className="hero-card">
          <span className="topo-texture" aria-hidden="true" />
          <div className="hero-tag-row">
            <span className="hero-id">
              CIMA <span>· {TIER_LABEL[score?.tier ?? "missed"].toUpperCase()}</span>
            </span>
            <span className="hero-date">{friendlyDateLabel(date)}</span>
          </div>
          <div className="hero-bracket">
            <span className="hero-bracket-mark tl" aria-hidden="true" />
            <span className="hero-bracket-mark tr" aria-hidden="true" />
            <span className="hero-bracket-mark bl" aria-hidden="true" />
            <span className="hero-bracket-mark br" aria-hidden="true" />
            <div className="hero-pct">
              {Math.round(completion * 100)}
              <span className="hero-pct-sym">%</span>
            </div>
            <div className="hero-sub">
              {dueHabits.length > 0 ? `Completado · ${doneCount} de ${dueHabits.length}` : "Día libre"}
            </div>
          </div>
          <div className="hero-stat-strip">
            <div className="hero-stat">
              <strong>{score?.streak ?? 0}</strong>
              <span>Racha días</span>
            </div>
            <div className="hero-stat">
              <strong>{runningStats ? formatKm(runningStats.km_month) : "0"}</strong>
              <span>Km mes</span>
            </div>
            <div className="hero-stat">
              <strong>{score && score.points > 0 ? `+${score.points}` : "0"}</strong>
              <span>Puntos</span>
            </div>
          </div>
        </div>

        {/* --- Tira de la última semana: un aro por día, coloreado por nivel --- */}
        <div className="week-strip">
          {week.map((d) => {
            const selected = d.date === date;
            const rate = d.completion_rate ?? 0;
            return (
              <button
                key={d.date}
                className={`week-day tier-${d.tier} ${selected ? "selected" : ""}`}
                onClick={() => setDate(d.date)}
                aria-label={`${weekdayInitial(d.date)} · ${Math.round(rate * 100)}%`}
              >
                <span className="week-dot">
                  {d.tier === "perfect" ? (
                    <CheckIcon size={16} strokeWidth={2.4} />
                  ) : d.tier === "rest" ? (
                    "·"
                  ) : (
                    Math.round(rate * 100)
                  )}
                </span>
                <span className="week-label">{weekdayInitial(d.date)}</span>
              </button>
            );
          })}
        </div>

        {/* --- Lo que toca hoy (plan generado por el coach o manual) --- */}
        {planned && (
          <div className="plan-card">
            <span className="plan-icon">
              {planned.workout_type === "RUNNING" ? (
                <SunIcon size={22} />
              ) : planned.workout_type ? (
                <BarbellIcon size={22} />
              ) : (
                <LeafIcon size={22} />
              )}
            </span>
            <div className="plan-body">
              <span className="plan-kicker">
                {isToday ? "Hoy toca" : "Ese día toca"}
                {planned.source === "ai" && <span className="plan-ai">coach IA</span>}
              </span>
              <strong>{planned.title}</strong>
              {planned.details && <p>{planned.details}</p>}
            </div>
          </div>
        )}

        {/* --- Semana completa: qué días tocan carrera (y de qué tipo) o gym --- */}
        <WeekPlan />

        {periodization && (
          <div className="banner">
            <strong>{periodization.label}</strong> · {periodization.rir_target}
            <p style={{ color: "inherit", opacity: 0.85, margin: "4px 0 0" }}>
              {periodization.description}
            </p>
          </div>
        )}

        <div className="card">
          <h2>{isToday ? "Checklist de hoy" : `Checklist · ${friendlyDateLabel(date)}`}</h2>
          {loading && <p>Cargando…</p>}
          {!loading && dueHabits.length === 0 && (
            <p className="empty-state">Nada programado este día. Descansa.</p>
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
