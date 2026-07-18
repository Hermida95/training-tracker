import { useEffect, useState } from "react";
import { habitsApi } from "../api/habits";
import type { Habit, HabitValueType } from "../types";

const DAY_LABELS = ["L", "M", "X", "J", "V", "S", "D"]; // 0=Lunes ... 6=Domingo

// Genera la key estable que exige el backend a partir del nombre visible:
// "1h de estudio" -> "1h_de_estudio". Si chocara con una existente, el
// backend devuelve 409 y se muestra el error tal cual.
function slugify(name: string): string {
  return name
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

interface DayPickerProps {
  value: number[];
  onChange: (days: number[]) => void;
}

function DayPicker({ value, onChange }: DayPickerProps) {
  const toggle = (day: number) =>
    onChange(value.includes(day) ? value.filter((d) => d !== day) : [...value, day].sort());

  return (
    <div className="day-picker">
      {DAY_LABELS.map((label, day) => (
        <button
          key={day}
          type="button"
          className={`day-chip ${value.includes(day) ? "on" : ""}`}
          onClick={() => toggle(day)}
          aria-pressed={value.includes(day)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

export function HabitManager() {
  const [habits, setHabits] = useState<Habit[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Formulario de alta
  const [name, setName] = useState("");
  const [valueType, setValueType] = useState<HabitValueType>("boolean");
  const [target, setTarget] = useState("");
  const [unit, setUnit] = useState("");
  const [days, setDays] = useState<number[]>([0, 1, 2, 3, 4, 5, 6]);
  const [saving, setSaving] = useState(false);

  const load = () => habitsApi.list().then(setHabits);
  useEffect(() => {
    load();
  }, []);

  const create = async () => {
    if (!name.trim() || days.length === 0) return;
    setSaving(true);
    setError(null);
    try {
      await habitsApi.create({
        key: slugify(name),
        name: name.trim(),
        value_type: valueType,
        target_value: valueType === "numeric" && target ? Number(target) : null,
        unit: valueType === "numeric" && unit.trim() ? unit.trim() : null,
        active_days: days,
        sort_order: habits.length + 1,
      });
      setName("");
      setTarget("");
      setUnit("");
      setValueType("boolean");
      setDays([0, 1, 2, 3, 4, 5, 6]);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al crear el hábito");
    } finally {
      setSaving(false);
    }
  };

  const updateDays = async (habit: Habit, newDays: number[]) => {
    if (newDays.length === 0) return; // un hábito sin días activos no tiene sentido
    await habitsApi.update(habit.id, { active_days: newDays });
    await load();
  };

  const remove = async (habit: Habit) => {
    if (!window.confirm(`¿Borrar "${habit.name}" y todo su historial?`)) return;
    await habitsApi.remove(habit.id);
    await load();
  };

  return (
    <div className="card">
      <h2>Mis hábitos</h2>
      <p style={{ fontSize: "0.82rem" }}>
        Añade tareas personalizadas (ej. "1h de estudio", "1h de lectura") y elige qué días
        aparecen en el checklist de Hoy.
      </p>

      {habits.map((habit) => (
        <div className="habit-manage-row" key={habit.id}>
          <div className="habit-manage-head">
            <div className="info">
              <span>{habit.name}</span>
              {habit.target_value !== null && (
                <span className="streak">
                  objetivo: {habit.target_value} {habit.unit ?? ""}
                </span>
              )}
            </div>
            <button
              className="danger"
              style={{ minHeight: 40, padding: "6px 12px" }}
              onClick={() => remove(habit)}
              aria-label={`Borrar ${habit.name}`}
            >
              Borrar
            </button>
          </div>
          <DayPicker value={habit.active_days} onChange={(d) => updateDays(habit, d)} />
        </div>
      ))}

      <div className="habit-create-form">
        <h2 style={{ marginTop: 16 }}>Nuevo hábito</h2>
        <label>Nombre</label>
        <input
          type="text"
          placeholder="1h de estudio"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />

        <label style={{ marginTop: 10, display: "block" }}>Tipo</label>
        <div className="btn-row">
          <button
            type="button"
            className={valueType === "boolean" ? "primary" : ""}
            onClick={() => setValueType("boolean")}
          >
            Hecho / no hecho
          </button>
          <button
            type="button"
            className={valueType === "numeric" ? "primary" : ""}
            onClick={() => setValueType("numeric")}
          >
            Con objetivo
          </button>
        </div>

        {valueType === "numeric" && (
          <div className="btn-row" style={{ marginTop: 10 }}>
            <div style={{ flex: 1 }}>
              <label>Objetivo</label>
              <input
                type="number"
                inputMode="decimal"
                placeholder="60"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
              />
            </div>
            <div style={{ flex: 1 }}>
              <label>Unidad</label>
              <input
                type="text"
                placeholder="min"
                value={unit}
                onChange={(e) => setUnit(e.target.value)}
              />
            </div>
          </div>
        )}

        <label style={{ marginTop: 10, display: "block" }}>Días</label>
        <DayPicker value={days} onChange={setDays} />

        {error && <p style={{ color: "var(--danger)" }}>{error}</p>}

        <button
          className="primary big"
          style={{ marginTop: 12 }}
          onClick={create}
          disabled={saving || !name.trim() || days.length === 0}
        >
          {saving ? "Creando…" : "Añadir hábito"}
        </button>
      </div>
    </div>
  );
}
