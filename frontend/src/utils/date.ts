// La app asume siempre Europe/Madrid (igual que el backend, ver APP_TIMEZONE),
// así que "hoy" se calcula en esa zona explícitamente en vez de con
// `Date.toISOString()` (UTC) o el reloj local del dispositivo: cerca de
// medianoche ambos pueden dar el día equivocado (ej. 00:30 CEST del domingo
// es todavía 22:30 UTC del sábado).
const TIMEZONE = "Europe/Madrid";

// El locale "en-CA" formatea fechas como YYYY-MM-DD, que es justo lo que
// necesitamos para mandar a la API.
const formatter = new Intl.DateTimeFormat("en-CA", { timeZone: TIMEZONE });

export function todayIsoMadrid(): string {
  return formatter.format(new Date());
}

/** 0=Lunes ... 6=Domingo, calculado en Europe/Madrid (no en la zona del dispositivo). */
export function weekdayMadrid(): number {
  const short = new Intl.DateTimeFormat("en-US", { timeZone: TIMEZONE, weekday: "short" }).format(
    new Date()
  );
  const map: Record<string, number> = { Mon: 0, Tue: 1, Wed: 2, Thu: 3, Fri: 4, Sat: 5, Sun: 6 };
  return map[short];
}

// --- Aritmética sobre fechas ISO (YYYY-MM-DD) sin líos de zona horaria ---
// Trabajamos con la fecha "civil" (sin hora): construimos el Date a mediodía
// UTC para que sumar/restar días nunca cruce un límite de día por el offset.

export function addDaysIso(iso: string, days: number): string {
  const d = new Date(`${iso}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

export function isFutureIso(iso: string): boolean {
  return iso > todayIsoMadrid();
}

/** Etiqueta corta para el día seleccionado: "Hoy", "Ayer" o "mié 22 jul". */
export function friendlyDateLabel(iso: string): string {
  const today = todayIsoMadrid();
  if (iso === today) return "Hoy";
  if (iso === addDaysIso(today, -1)) return "Ayer";
  const d = new Date(`${iso}T12:00:00Z`);
  return new Intl.DateTimeFormat("es-ES", {
    weekday: "short",
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  }).format(d);
}

/** Inicial del día de la semana (L M X J V S D) para la fecha ISO dada. */
export function weekdayInitial(iso: string): string {
  const d = new Date(`${iso}T12:00:00Z`);
  return ["D", "L", "M", "X", "J", "V", "S"][d.getUTCDay()];
}
