// Duplica (en TS) el cálculo de horarios de public/sw.js. No se comparte
// código entre ambos porque el service worker se sirve tal cual desde
// /public (Vite no lo procesa) y no puede importar módulos TS del bundle
// sin añadir un paso de build extra que no aporta nada aquí: es un cálculo
// de ~30 líneas, más simple duplicarlo que montar tooling para compartirlo.
import type { BreakConfig } from "../types";

function offsetMinutesAt(date: Date, timeZone: string): number {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone,
    hour12: false,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).formatToParts(date);
  const get = (type: string) => parts.find((p) => p.type === type)!.value;
  const hour = get("hour") === "24" ? "00" : get("hour");
  const asUtc = Date.UTC(
    Number(get("year")),
    Number(get("month")) - 1,
    Number(get("day")),
    Number(hour),
    Number(get("minute")),
    Number(get("second"))
  );
  return (asUtc - date.getTime()) / 60000;
}

function zonedWallTimeToUtc(
  year: number,
  month: number,
  day: number,
  hour: number,
  minute: number,
  timeZone: string
): Date {
  const guess = new Date(Date.UTC(year, month - 1, day, hour, minute));
  const offset = offsetMinutesAt(guess, timeZone);
  return new Date(guess.getTime() - offset * 60000);
}

function weekdayInZone(date: Date, timeZone: string): number {
  const wd = new Intl.DateTimeFormat("en-US", { timeZone, weekday: "short" }).format(date);
  const map: Record<string, number> = { Mon: 0, Tue: 1, Wed: 2, Thu: 3, Fri: 4, Sat: 5, Sun: 6 };
  return map[wd];
}

function ymdInZone(date: Date, timeZone: string) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);
  const get = (type: string) => Number(parts.find((p) => p.type === type)!.value);
  return { year: get("year"), month: get("month"), day: get("day") };
}

/** Próximo instante (Date) en el que debería sonar la alarma, o null si no hay ninguno en `daysAhead` días. */
export function computeNextBreakTime(config: BreakConfig, daysAhead = 2): Date | null {
  const { interval_minutes, window_start, window_end, timezone, active_weekdays } = config;
  const [startH, startM] = window_start.split(":").map(Number);
  const [endH, endM] = window_end.split(":").map(Number);
  const weekdays = active_weekdays?.length ? active_weekdays : [0, 1, 2, 3, 4];
  const now = new Date();

  for (let d = 0; d < daysAhead; d++) {
    const cursor = new Date(now.getTime() + d * 86400000);
    const { year, month, day } = ymdInZone(cursor, timezone);
    if (!weekdays.includes(weekdayInZone(cursor, timezone))) continue;

    const dayStart = zonedWallTimeToUtc(year, month, day, startH, startM, timezone);
    const dayEnd = zonedWallTimeToUtc(year, month, day, endH, endM, timezone);

    for (let t = dayStart.getTime(); t <= dayEnd.getTime(); t += interval_minutes * 60000) {
      if (t > now.getTime()) return new Date(t);
    }
  }
  return null;
}
