import { useEffect, useState } from "react";
import { plannedApi } from "../api/planned";
import type { PlannedWorkout } from "../types";
import { addDaysIso, todayIsoMadrid, weekdayMadrid } from "../utils/date";
import { BarbellIcon, LeafIcon, SunIcon } from "./icons";

const WEEKDAY_LABEL = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
const WEEKDAY_SHORT = ["L", "M", "X", "J", "V", "S", "D"];

function planIcon(type: PlannedWorkout["workout_type"] | undefined) {
  if (type === "RUNNING") return <SunIcon size={18} />;
  if (type) return <BarbellIcon size={18} />;
  return <LeafIcon size={18} />;
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
      <h2>Plan de la semana</h2>
      {days.map((day, i) => {
        const date = addDaysIso(weekStart, i);
        const isToday = date === todayIsoMadrid();
        return (
          <div className={`week-plan-row ${isToday ? "today" : ""}`} key={date}>
            <span className="week-plan-day">{WEEKDAY_SHORT[i]}</span>
            <span className={`week-plan-icon ${day?.workout_type === "RUNNING" ? "running" : ""}`}>
              {planIcon(day?.workout_type)}
            </span>
            <div className="week-plan-body">
              <strong>{day?.title ?? "Descanso"}</strong>
              {day?.details && <p>{day.details}</p>}
            </div>
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
