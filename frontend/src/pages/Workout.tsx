import { useEffect, useState } from "react";
import { workoutsApi } from "../api/workouts";
import { Stepper } from "../components/Stepper";
import type {
  ExerciseTemplate,
  PeriodizationInfo,
  SessionComparison,
  WorkoutSet,
  WorkoutType,
} from "../types";
import { todayIsoMadrid as todayIso, weekdayMadrid } from "../utils/date";

// Sugerencia por defecto según el día de la semana (Lun=0 ... Dom=6),
// siguiendo el checklist del spec: L/X/V gym, Sáb running.
const SUGGESTED_TYPE: Record<number, WorkoutType | null> = {
  0: "GYM1",
  1: null,
  2: "GYM2",
  3: null,
  4: "GYM3",
  5: "RUNNING",
  6: null,
};

const TYPE_LABEL: Record<WorkoutType, string> = {
  GYM1: "GYM 1 · Lunes",
  GYM2: "GYM 2 · Miércoles",
  GYM3: "GYM 3 · Viernes",
  RUNNING: "Running · Sábado",
  CUSTOM: "Personalizado",
};

interface DraftExercise {
  template: ExerciseTemplate;
  sets: WorkoutSet[];
}

export default function Workout() {
  const [workoutType, setWorkoutType] = useState<WorkoutType>(
    SUGGESTED_TYPE[weekdayMadrid()] ?? "GYM1"
  );
  const [periodization, setPeriodization] = useState<PeriodizationInfo | null>(null);
  const [draft, setDraft] = useState<DraftExercise[]>([]);
  const [runningMinutes, setRunningMinutes] = useState<number | null>(null);
  const [runningFeeling, setRunningFeeling] = useState<number | null>(null);
  const [comparison, setComparison] = useState<SessionComparison | null>(null);
  const [saving, setSaving] = useState(false);
  const [savedSessionId, setSavedSessionId] = useState<number | null>(null);

  useEffect(() => {
    setComparison(null);
    setSavedSessionId(null);

    if (workoutType === "RUNNING" || workoutType === "CUSTOM") {
      workoutsApi.periodization(todayIso()).then(setPeriodization);
      setDraft([]);
      return;
    }

    Promise.all([
      workoutsApi.periodization(todayIso()),
      workoutsApi.templates(workoutType),
    ]).then(([p, templates]) => {
      setPeriodization(p);
      const adjust = (base: number | null) =>
        base === null ? null : Math.round((base + p.weight_adjustment_kg) * 100) / 100;

      setDraft(
        templates.map((t) => ({
          template: t,
          sets: Array.from({ length: t.target_sets }, (_, i) => ({
            set_number: i + 1,
            weight_kg: adjust(t.base_weight_kg),
            reps: null,
          })),
        }))
      );
    });
  }, [workoutType]);

  const updateSet = (exIndex: number, setIndex: number, patch: Partial<WorkoutSet>) => {
    setDraft((prev) => {
      const next = [...prev];
      const sets = [...next[exIndex].sets];
      sets[setIndex] = { ...sets[setIndex], ...patch };
      next[exIndex] = { ...next[exIndex], sets };
      return next;
    });
  };

  const save = async () => {
    setSaving(true);
    try {
      const exercises =
        workoutType === "RUNNING"
          ? []
          : draft.map((d, i) => ({
              name: d.template.name,
              order: i + 1,
              exercise_template_id: d.template.id,
              sets: d.sets,
            }));

      const session = await workoutsApi.create({
        date: todayIso(),
        workout_type: workoutType,
        running_minutes: workoutType === "RUNNING" ? runningMinutes : null,
        running_feeling: workoutType === "RUNNING" ? runningFeeling : null,
        exercises,
      });
      setSavedSessionId(session.id);
      if (workoutType !== "RUNNING") {
        const cmp = await workoutsApi.comparison(session.id);
        setComparison(cmp);
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div className="top-bar">
        <h1>Entreno</h1>
      </div>
      <main>
        <div className="card">
          <select value={workoutType} onChange={(e) => setWorkoutType(e.target.value as WorkoutType)}>
            {(Object.keys(TYPE_LABEL) as WorkoutType[]).map((t) => (
              <option key={t} value={t}>
                {TYPE_LABEL[t]}
              </option>
            ))}
          </select>
          {periodization && (
            <p style={{ marginTop: 8 }}>
              {periodization.label} · {periodization.rir_target}
              {periodization.weight_adjustment_kg !== 0 &&
                ` · +${periodization.weight_adjustment_kg}kg`}
              {periodization.set_adjustment !== 0 &&
                ` · ${periodization.set_adjustment} series`}
            </p>
          )}
        </div>

        {workoutType === "RUNNING" ? (
          <div className="card">
            <h2>Running Z2</h2>
            <label>Minutos</label>
            <Stepper value={runningMinutes} step={5} onChange={setRunningMinutes} suffix=" min" />
            <label style={{ marginTop: 12, display: "block" }}>Sensaciones (1-5)</label>
            <div className="btn-row">
              {[1, 2, 3, 4, 5].map((n) => (
                <button
                  key={n}
                  className={runningFeeling === n ? "primary" : ""}
                  onClick={() => setRunningFeeling(n)}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>
        ) : (
          draft.map((d, exIndex) => (
            <div className="card" key={d.template.id}>
              <h2>
                {d.template.name}{" "}
                <span style={{ fontWeight: 400 }}>· {d.template.target_reps}</span>
              </h2>
              {d.sets.map((set, setIndex) => (
                <div className="set-row" key={set.set_number}>
                  <span className="set-index">{set.set_number}</span>
                  <Stepper
                    value={set.weight_kg}
                    step={2.5}
                    suffix="kg"
                    onChange={(v) => updateSet(exIndex, setIndex, { weight_kg: v })}
                  />
                  <Stepper
                    value={set.reps}
                    step={1}
                    suffix=" reps"
                    onChange={(v) => updateSet(exIndex, setIndex, { reps: v })}
                  />
                </div>
              ))}
            </div>
          ))
        )}

        <button className="primary big" onClick={save} disabled={saving}>
          {saving ? "Guardando…" : "Guardar sesión"}
        </button>

        {savedSessionId && !comparison && workoutType === "RUNNING" && (
          <p style={{ marginTop: 12 }}>Sesión guardada ✓</p>
        )}

        {comparison && (
          <div className="card" style={{ marginTop: 12 }}>
            <h2>Vs. sesión anterior</h2>
            {comparison.previous_session_id === null && (
              <p>Primera sesión de este tipo, sin comparación todavía.</p>
            )}
            {comparison.exercises.map((ex) => (
              <div key={ex.name} style={{ marginBottom: 10 }}>
                <strong>{ex.name}</strong>
                {ex.sets.map((s) => (
                  <div key={s.set_number} className="set-row">
                    <span className="set-index">{s.set_number}</span>
                    <span>
                      {s.current_weight_kg ?? "-"}kg x{s.current_reps ?? "-"}
                    </span>
                    <span
                      className={`delta ${
                        s.weight_delta_kg === null
                          ? "flat"
                          : s.weight_delta_kg > 0
                            ? "up"
                            : s.weight_delta_kg < 0
                              ? "down"
                              : "flat"
                      }`}
                    >
                      {s.weight_delta_kg === null
                        ? "sin datos previos"
                        : `${s.weight_delta_kg > 0 ? "+" : ""}${s.weight_delta_kg}kg`}
                    </span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
