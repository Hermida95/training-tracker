import { useCallback, useEffect, useRef, useState } from "react";
import { workoutsApi } from "../api/workouts";
import { CheckIcon } from "../components/icons";
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
// Plan híbrido: gym Lun/Mié/Vie, running Mar/Jue/Sáb.
const SUGGESTED_TYPE: Record<number, WorkoutType> = {
  0: "GYM1",
  1: "RUNNING",
  2: "GYM2",
  3: "RUNNING",
  4: "GYM3",
  5: "RUNNING",
  6: "RUNNING",
};

const TYPE_LABEL: Record<WorkoutType, string> = {
  GYM1: "Gym A · Lunes",
  GYM2: "Gym B · Miércoles",
  GYM3: "Gym C · Viernes",
  RUNNING: "Running / Rodaje",
  CUSTOM: "Personalizado",
};

const isGym = (t: WorkoutType) => t === "GYM1" || t === "GYM2" || t === "GYM3";

interface DraftExercise {
  name: string;
  templateId: number | null;
  sets: WorkoutSet[];
}

type SaveState = "idle" | "saving" | "saved" | "error";

export default function Workout() {
  const [workoutType, setWorkoutType] = useState<WorkoutType>(
    SUGGESTED_TYPE[weekdayMadrid()]
  );
  const [periodization, setPeriodization] = useState<PeriodizationInfo | null>(null);
  const [draft, setDraft] = useState<DraftExercise[]>([]);
  const [comparison, setComparison] = useState<SessionComparison | null>(null);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [completed, setCompleted] = useState(false);
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [editingRoutine, setEditingRoutine] = useState(false);
  const [loading, setLoading] = useState(true);

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

  // Reanuda la sesión de hoy de este tipo si existe; si no, construye el
  // borrador desde la rutina del usuario (solo para gym).
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
      const session = existing[0];
      setSessionId(session.id);
      setCompleted(session.completed);
      setDraft(isGym(workoutType) ? draftFromSession(session) : []);
      setSaveState("saved");
    } else {
      setSessionId(null);
      setCompleted(false);
      if (isGym(workoutType)) {
        const templates = await workoutsApi.templates(workoutType);
        setDraft(buildDraftFromTemplates(templates, p));
      } else {
        setDraft([]);
      }
    }
    setLoading(false);
  }, [workoutType]);

  useEffect(() => {
    loadForType();
  }, [loadForType]);

  const buildPayload = useCallback(
    (markCompleted?: boolean) => ({
      date: todayIso(),
      workout_type: workoutType,
      completed: markCompleted ?? completed,
      exercises: isGym(workoutType)
        ? draft.map((d, i) => ({
            name: d.name,
            order: i + 1,
            exercise_template_id: d.templateId,
            sets: d.sets,
          }))
        : [],
    }),
    [workoutType, completed, draft]
  );

  // Autosave de gym: cada cambio del borrador se persiste (debounced). Crea la
  // sesión en la primera escritura y la actualiza después. Si la app se cierra
  // a media sesión, lo registrado NO se pierde.
  useEffect(() => {
    if (loading || !isGym(workoutType)) return;
    if (!hydrated.current) {
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
  }, [buildPayload, loading, sessionId, workoutType]);

  const updateSet = (exIndex: number, setIndex: number, patch: Partial<WorkoutSet>) => {
    setDraft((prev) => {
      const next = [...prev];
      const sets = [...next[exIndex].sets];
      sets[setIndex] = { ...sets[setIndex], ...patch };
      next[exIndex] = { ...next[exIndex], sets };
      return next;
    });
  };

  // Marca la sesión como hecha (crea si hace falta). withComparison trae la
  // comparación con la sesión anterior (gym detallado).
  const markDone = async (withComparison: boolean) => {
    if (saveTimer.current) clearTimeout(saveTimer.current);
    setSaveState("saving");
    try {
      const payload = buildPayload(true);
      const session =
        sessionId === null
          ? await workoutsApi.create(payload)
          : await workoutsApi.update(sessionId, payload);
      setSessionId(session.id);
      setCompleted(true);
      setSaveState("saved");
      if (withComparison && isGym(workoutType)) {
        setComparison(await workoutsApi.comparison(session.id));
      }
    } catch {
      setSaveState("error");
    }
  };

  const undoDone = async () => {
    setComparison(null);
    if (sessionId === null) {
      setCompleted(false);
      return;
    }
    if (isGym(workoutType)) {
      // Gym: mantiene lo registrado, solo vuelve a "en curso".
      await workoutsApi.update(sessionId, buildPayload(false));
      setCompleted(false);
    } else {
      // Running: no había nada registrado, así que deshacer = borrar la sesión.
      await workoutsApi.remove(sessionId);
      setSessionId(null);
      setCompleted(false);
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
        {isGym(workoutType) && saveState !== "idle" && (
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
          {isGym(workoutType) && periodization && (
            <p style={{ marginTop: 8 }}>
              {periodization.label} · {periodization.rir_target}
              {periodization.weight_adjustment_kg !== 0 &&
                ` · +${periodization.weight_adjustment_kg}kg`}
              {periodization.set_adjustment !== 0 && ` · ${periodization.set_adjustment} series`}
            </p>
          )}
          {isGym(workoutType) && (
            <button
              className="ghost"
              style={{ width: "100%", marginTop: 10 }}
              onClick={() => setEditingRoutine((v) => !v)}
            >
              {editingRoutine ? "Cerrar editor" : "Editar rutina"}
            </button>
          )}
        </div>

        {/* Estado hecho: banner con deshacer, para gym y running */}
        {completed && !editingRoutine && (
          <div className="done-banner">
            <span className="done-icon">
              <CheckIcon size={22} strokeWidth={2.4} />
            </span>
            <strong>Entreno de hoy hecho</strong>
            <button className="ghost" onClick={undoDone}>
              Deshacer
            </button>
          </div>
        )}

        {editingRoutine && isGym(workoutType) ? (
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
        ) : !isGym(workoutType) ? (
          // --- RUNNING: solo marcar hecho ---
          !completed && (
            <div className="card">
              <h2>Rodaje de hoy</h2>
              <p>
                Márcalo hecho cuando lo termines. El detalle (ritmo, distancia) lo llevas en tu
                reloj; aquí solo cuenta que lo hiciste.
              </p>
              <button className="primary big" onClick={() => markDone(false)}>
                Marcar rodaje hecho
              </button>
            </div>
          )
        ) : (
          // --- GYM: registro de series + atajos ---
          <>
            {!completed && (
              <button
                className="ghost mark-quick"
                onClick={() => markDone(false)}
                title="Para los días que ya lo llevas en el Garmin"
              >
                Marcar hecho sin registrar
              </button>
            )}

            {draft.length === 0 ? (
              <div className="card">
                <p className="empty-state">
                  Esta rutina no tiene ejercicios. Pulsa "Editar rutina" para añadirlos.
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

            {!completed && draft.length > 0 && (
              <button className="primary big" onClick={() => markDone(true)}>
                Terminar y comparar
              </button>
            )}
          </>
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
