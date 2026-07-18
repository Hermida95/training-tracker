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
