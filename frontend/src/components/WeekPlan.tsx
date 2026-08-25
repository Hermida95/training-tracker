import { useEffect, useState } from "react";
import { plannedApi } from "../api/planned";
import type { PlannedWorkout } from "../types";
import { addDaysIso, todayIsoMadrid, weekdayMadrid } from "../utils/date";

const WEEKDAY_LABEL = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
const WEEKDAY_SHORT = ["L", "M", "X", "J", "V", "S", "D"];

// Etiqueta de spec: la categoría fiable que tenemos es workout_type, no el
// tipo exacto de rodaje (Z2/series/tirada larga viven como texto libre en
// title/details, generado por el coach — no hay forma fiable de parsearlo).
function kindTag(type: PlannedWorkout["workout_type"] | undefined): string {
  if (type === "RUNNING") return "Run";
  if (type) return "Gym";
  return "Rest";
}

/** Plan de la semana en curso, día a día, con opción de mover/intercambiar
 * cada entreno a otro día (para cuando un día no se puede entrenar). */
export function WeekPlan() {
  const [weekStart, setWeekStart] = useState<string | null>(null);
  const [days, setDays] = useState<(PlannedWorkout | null)[]>([]);
  const [movingId, setMovingId] = useState<number | null>(null);

  const load = () => {
    const start = addDaysIso(todayIsoMadrid(), -weekdayMadrid());
    setWeekStart(start);
    plannedApi.week(start, addDaysIso(start, 6)).then((planned) => {
      const byDate = new Map(planned.map((p) => [p.date, p]));
      setDays(Array.from({ length: 7 }, (_, i) => byDate.get(addDaysIso(start, i)) ?? null));
    });
  };

  useEffect(load, []);

  const move = async (id: number, toDate: string) => {
    setMovingId(id);
    try {
      await plannedApi.move(id, toDate);
    } finally {
      setMovingId(null);
      load();
    }
  };

  // Sin plan generado esta semana: no hay nada útil que enseñar aquí.
  if (!weekStart || days.every((d) => d === null)) return null;

  return (
    <div className="card week-plan">
      <h2>Plan semana</h2>
      {days.map((day, i) => {
        const date = addDaysIso(weekStart, i);
        const isToday = date === todayIsoMadrid();
        return (
          <div className={`week-plan-row ${isToday ? "today" : ""}`} key={date}>
            <span className="week-plan-day">{WEEKDAY_SHORT[i]}</span>
            <div className="week-plan-body">
              <strong>{day?.title ?? "Descanso activo"}</strong>
            </div>
            <span className={`week-plan-kind ${day?.workout_type === "RUNNING" ? "run" : ""}`}>
              {kindTag(day?.workout_type)}
            </span>
            {day && (
              <select
                className="week-plan-move"
                value=""
                disabled={movingId === day.id}
                onChange={(e) => {
                  if (e.target.value) move(day.id, e.target.value);
                }}
                aria-label={`Mover lo de ${WEEKDAY_LABEL[i]} a otro día`}
              >
                <option value="">Mover…</option>
                {WEEKDAY_LABEL.map(
                  (label, j) =>
                    j !== i && (
                      <option key={j} value={addDaysIso(weekStart, j)}>
                        {label}
                      </option>
                    )
                )}
              </select>
            )}
          </div>
        );
      })}
    </div>
  );
}
