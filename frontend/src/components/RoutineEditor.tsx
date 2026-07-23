import { useEffect, useState } from "react";
import { workoutsApi } from "../api/workouts";
import type { ExerciseTemplate, WorkoutType } from "../types";

interface RoutineEditorProps {
  workoutType: WorkoutType;
  typeLabel: string;
  onClose: () => void;
}

/** Editor de la rutina personal: añade, edita y borra los ejercicios de un día.
 *  Cada usuario construye así su propio entreno en vez de quedarse con el
 *  precargado. Los cambios afectan a las plantillas (ExerciseTemplate) que
 *  luego rellenan el borrador de la sesión. */
export function RoutineEditor({ workoutType, typeLabel, onClose }: RoutineEditorProps) {
  const [templates, setTemplates] = useState<ExerciseTemplate[]>([]);
  const [name, setName] = useState("");
  const [sets, setSets] = useState("3");
  const [reps, setReps] = useState("8-10");
  const [weight, setWeight] = useState("");
  const [saving, setSaving] = useState(false);

  const load = () => workoutsApi.templates(workoutType).then(setTemplates);
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workoutType]);

  const add = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      await workoutsApi.createTemplate({
        workout_type: workoutType,
        name: name.trim(),
        target_sets: Number(sets) || 3,
        target_reps: reps.trim(),
        base_weight_kg: weight.trim() ? Number(weight) : null,
      });
      setName("");
      setWeight("");
      await load();
    } finally {
      setSaving(false);
    }
  };

  const patch = async (tpl: ExerciseTemplate, data: Partial<ExerciseTemplate>) => {
    await workoutsApi.updateTemplate(tpl.id, data);
    await load();
  };

  const remove = async (tpl: ExerciseTemplate) => {
    if (!window.confirm(`¿Quitar "${tpl.name}" de la rutina?`)) return;
    await workoutsApi.deleteTemplate(tpl.id);
    await load();
  };

  return (
    <div className="card">
      <h2>Editar rutina · {typeLabel}</h2>
      <p style={{ fontSize: "0.82rem" }}>
        Estos ejercicios son los que aparecerán al registrar este entreno. El peso es el de la
        semana 1; la periodización lo ajusta sola.
      </p>

      {templates.map((tpl) => (
        <div className="routine-row" key={tpl.id}>
          <input
            className="routine-name"
            value={tpl.name}
            onChange={(e) =>
              setTemplates((prev) =>
                prev.map((t) => (t.id === tpl.id ? { ...t, name: e.target.value } : t))
              )
            }
            onBlur={(e) => {
              if (e.target.value.trim() && e.target.value !== tpl.name) {
                patch(tpl, { name: e.target.value.trim() });
              }
            }}
          />
          <div className="routine-fields">
            <label>
              Series
              <input
                type="number"
                inputMode="numeric"
                min={1}
                max={10}
                defaultValue={tpl.target_sets}
                onBlur={(e) => patch(tpl, { target_sets: Number(e.target.value) || 3 })}
              />
            </label>
            <label>
              Reps
              <input
                type="text"
                defaultValue={tpl.target_reps}
                onBlur={(e) => patch(tpl, { target_reps: e.target.value.trim() })}
              />
            </label>
            <label>
              Peso
              <input
                type="number"
                inputMode="decimal"
                defaultValue={tpl.base_weight_kg ?? ""}
                onBlur={(e) =>
                  patch(tpl, { base_weight_kg: e.target.value.trim() ? Number(e.target.value) : null })
                }
              />
            </label>
          </div>
          <button className="danger routine-del" onClick={() => remove(tpl)} aria-label="Quitar">
            Quitar
          </button>
        </div>
      ))}

      <div className="routine-add">
        <h2 style={{ marginTop: 8 }}>Añadir ejercicio</h2>
        <input
          type="text"
          placeholder="Nombre del ejercicio"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <div className="routine-fields" style={{ marginTop: 8 }}>
          <label>
            Series
            <input type="number" inputMode="numeric" value={sets} onChange={(e) => setSets(e.target.value)} />
          </label>
          <label>
            Reps
            <input type="text" value={reps} onChange={(e) => setReps(e.target.value)} />
          </label>
          <label>
            Peso
            <input
              type="number"
              inputMode="decimal"
              placeholder="kg"
              value={weight}
              onChange={(e) => setWeight(e.target.value)}
            />
          </label>
        </div>
        <button
          className="primary"
          style={{ width: "100%", marginTop: 10 }}
          onClick={add}
          disabled={saving || !name.trim()}
        >
          Añadir a la rutina
        </button>
      </div>

      <button className="ghost" style={{ width: "100%", marginTop: 10 }} onClick={onClose}>
        Hecho
      </button>
    </div>
  );
}
