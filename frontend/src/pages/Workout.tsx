import { useCallback, useEffect, useRef, useState } from "react";
import { workoutsApi } from "../api/workouts";
import { RoutineEditor } from "../components/RoutineEditor";
import { Stepper } from "../components/Stepper";
import type {
  ExerciseTemplate,
  PeriodizationInfo,
  SessionComparison,
  WorkoutSession,
  WorkoutSet,
  WorkoutType,
} from "../types";
import { todayIsoMadrid as todayIso, weekdayMadrid } from "../utils/date";

// Sugerencia por defecto según el día de la semana (Lun=0 ... Dom=6).
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
  name: string;
  templateId: number | null;
  sets: WorkoutSet[];
}

type SaveState = "idle" | "saving" | "saved" | "error";

export default function Workout() {
  const [workoutType, setWorkoutType] = useState<WorkoutType>(
    SUGGESTED_TYPE[weekdayMadrid()] ?? "GYM1"
  );
  const [periodization, setPeriodization] = useState<PeriodizationInfo | null>(null);
  const [draft, setDraft] = useState<DraftExercise[]>([]);
  const [runningMinutes, setRunningMinutes] = useState<number | null>(null);
  const [runningFeeling, setRunningFeeling] = useState<number | null>(null);
  const [comparison, setComparison] = useState<SessionComparison | null>(null);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [editingRoutine, setEditingRoutine] = useState(false);
  const [loading, setLoading] = useState(true);

  // Evita que el primer render (que rellena el draft) dispare un autosave.
  const hydrated = useRef(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const buildDraftFromTemplates = (templates: ExerciseTemplate[], p: PeriodizationInfo) => {
    const adjust = (base: number | null) =>
      base === null ? null : Math.round((base + p.weight_adjustment_kg) * 100) / 100;
    return templates.map((t) => ({
      name: t.name,
      templateId: t.id,
      sets: Array.from({ length: t.target_sets }, (_, i) => ({
        set_number: i + 1,
        weight_kg: adjust(t.base_weight_kg),
        reps: null,
      })),
    }));
  };

  const draftFromSession = (session: WorkoutSession): DraftExercise[] =>
    session.exercises.map((ex) => ({
      name: ex.name,
      templateId: ex.exercise_template_id,
      sets: ex.sets.map((s) => ({
        set_number: s.set_number,
        weight_kg: s.weight_kg,
        reps: s.reps,
      })),
    }));

  // Carga inicial al cambiar de tipo: reanuda la sesión de hoy si existe,
  // o construye el borrador desde la rutina (plantillas) del usuario.
  const loadForType = useCallback(async () => {
    hydrated.current = false;
    setLoading(true);
    setComparison(null);
    setSaveState("idle");

    const [p, existing] = await Promise.all([
      workoutsApi.periodization(todayIso()),
      workoutsApi.list({ workout_type: workoutType, start: todayIso(), end: todayIso(), limit: 1 }),
    ]);
    setPeriodization(p);

    if (existing.length > 0) {
      // Ya había una sesión de hoy de este tipo: la reanudamos (autosave previo).
      const session = existing[0];
      setSessionId(session.id);
      setDraft(draftFromSession(session));
      setRunningMinutes(session.running_minutes);
      setRunningFeeling(session.running_feeling);
      setSaveState("saved");
    } else {
      setSessionId(null);
      setRunningMinutes(null);
      setRunningFeeling(null);
      if (workoutType === "RUNNING" || workoutType === "CUSTOM") {
        setDraft([]);
      } else {
        const templates = await workoutsApi.templates(workoutType);
        setDraft(buildDraftFromTemplates(templates, p));
      }
    }
    setLoading(false);
    // Dejamos que el efecto de hidratación marque hydrated tras pintar.
  }, [workoutType]);

  useEffect(() => {
    loadForType();
  }, [loadForType]);

  const buildPayload = useCallback(
    () => ({
      date: todayIso(),
      workout_type: workoutType,
      running_minutes: workoutType === "RUNNING" ? runningMinutes : null,
      running_feeling: workoutType === "RUNNING" ? runningFeeling : null,
      exercises:
        workoutType === "RUNNING"
          ? []
          : draft.map((d, i) => ({
              name: d.name,
              order: i + 1,
              exercise_template_id: d.templateId,
              sets: d.sets,
            })),
    }),
    [workoutType, runningMinutes, runningFeeling, draft]
  );

  // Autosave: cada cambio del borrador se persiste (debounced). Crea la sesión
  // en la primera escritura y luego la actualiza. Así, si la app se cierra a
  // media sesión, lo registrado hasta ese momento NO se pierde.
  useEffect(() => {
    if (loading) return;
    if (!hydrated.current) {
      // Primer render tras cargar: no guardamos todavía (nada ha cambiado).
      hydrated.current = true;
      return;
    }
    if (saveTimer.current) clearTimeout(saveTimer.current);
    setSaveState("saving");
    saveTimer.current = setTimeout(async () => {
      try {
        const payload = buildPayload();
        if (sessionId === null) {
          const created = await workoutsApi.create(payload);
          setSessionId(created.id);
        } else {
          await workoutsApi.update(sessionId, payload);
        }
        setSaveState("saved");
      } catch {
        setSaveState("error");
      }
    }, 800);
    return () => {
      if (saveTimer.current) clearTimeout(saveTimer.current);
    };
    // buildPayload cambia con cualquier edición del borrador -> re-guarda.
  }, [buildPayload, loading, sessionId]);

  const updateSet = (exIndex: number, setIndex: number, patch: Partial<WorkoutSet>) => {
    setDraft((prev) => {
      const next = [...prev];
      const sets = [...next[exIndex].sets];
      sets[setIndex] = { ...sets[setIndex], ...patch };
      next[exIndex] = { ...next[exIndex], sets };
      return next;
    });
  };

  const finish = async () => {
    // Fuerza un guardado inmediato y trae la comparación con la sesión anterior.
    if (saveTimer.current) clearTimeout(saveTimer.current);
    setSaveState("saving");
    try {
      const payload = buildPayload();
      const session =
        sessionId === null
          ? await workoutsApi.create(payload)
          : await workoutsApi.update(sessionId, payload);
      setSessionId(session.id);
      setSaveState("saved");
      if (workoutType !== "RUNNING") {
        setComparison(await workoutsApi.comparison(session.id));
      }
    } catch {
      setSaveState("error");
    }
  };

  const saveLabel: Record<SaveState, string> = {
    idle: "",
    saving: "Guardando…",
    saved: "Guardado ✓",
    error: "Error al guardar",
  };

  return (
    <div>
      <div className="top-bar">
        <h1>Entreno</h1>
        {saveState !== "idle" && (
          <span className={`pill ${saveState === "error" ? "warn" : "ok"}`}>
            {saveLabel[saveState]}
          </span>
        )}
      </div>
      <main>
        <div className="card">
          <select
            value={workoutType}
            onChange={(e) => setWorkoutType(e.target.value as WorkoutType)}
          >
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
              {periodization.set_adjustment !== 0 && ` · ${periodization.set_adjustment} series`}
            </p>
          )}
          {workoutType !== "RUNNING" && (
            <button
              className="ghost"
              style={{ width: "100%", marginTop: 10 }}
              onClick={() => setEditingRoutine((v) => !v)}
            >
              {editingRoutine ? "Cerrar editor" : "Editar rutina"}
            </button>
          )}
        </div>

        {editingRoutine && workoutType !== "RUNNING" ? (
          <RoutineEditor
            workoutType={workoutType}
            typeLabel={TYPE_LABEL[workoutType]}
            onClose={() => {
              setEditingRoutine(false);
              loadForType();
            }}
          />
        ) : loading ? (
          <p className="empty-state">Cargando…</p>
        ) : workoutType === "RUNNING" ? (
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
        ) : draft.length === 0 ? (
          <div className="card">
            <p className="empty-state">
              Esta rutina no tiene ejercicios todavía. Pulsa "Editar rutina" para añadirlos.
            </p>
          </div>
        ) : (
          draft.map((d, exIndex) => (
            <div className="card" key={`${d.name}-${exIndex}`}>
              <h2>{d.name}</h2>
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

        {!editingRoutine && !loading && (
          <button className="primary big" onClick={finish}>
            Terminar y comparar
          </button>
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
