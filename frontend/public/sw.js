/**
 * Service worker de "Entreno & Hábitos".
 *
 * =========================================================================
 * ESTRATEGIA DE NOTIFICACIONES PROGRAMADAS (alarma antisedentarismo)
 * =========================================================================
 *
 * El objetivo: avisar cada 45-50 min, solo L-V 08:30-15:00 Europe/Madrid,
 * incluso con el móvil bloqueado y la app cerrada. Esto es más difícil de lo
 * que parece porque un service worker NO es un proceso siempre activo: el
 * navegador lo apaga en cuanto no tiene trabajo pendiente (evento fetch,
 * push, notificationclick...) para ahorrar batería. Un `setTimeout` de 45
 * minutos dentro de un SW casi nunca llega a dispararse si el usuario no ha
 * tocado la app en ese rato.
 *
 * Usamos dos mecanismos, en cascada, de más a menos fiable:
 *
 * 1) Notification Triggers API (`showTrigger: new TimestampTrigger(ts)`)
 *    Es la API pensada exactamente para esto: le pides al navegador que
 *    muestre una notificación en un instante futuro, y es EL NAVEGADOR (no
 *    tu JS) quien la dispara, aunque el service worker esté dormido o la
 *    app llevara horas cerrada. Soporte real hoy: Chrome/Edge en Android
 *    (activable en chrome://flags/#notification-triggers en desktop, nativo
 *    en algunas versiones de Android), NO soportado en iOS Safari ni Firefox
 *    a fecha de este proyecto. Por eso la usamos como mejora progresiva:
 *    `if ('showTrigger' in Notification.prototype)`.
 *
 * 2) Fallback client-side (ver src/hooks/useNotificationScheduler.ts)
 *    Mientras la PWA está abierta (foreground o recién puesta en background,
 *    dentro del budget de ejecución que da el SO), un `setTimeout` en la
 *    página programa la siguiente notificación. Esto NO sobrevive a que el
 *    usuario bloquee el móvil largo rato con la app cerrada, pero cubre el
 *    caso más común: llevas la app abierta durante la jornada de trabajo.
 *
 * PARA PRODUCCIÓN "A PRUEBA DE BALAS" (documentado en el README, no
 * implementado aquí para no añadir infraestructura que no se pidió):
 * la única forma 100% fiable de despertar el dispositivo con la app
 * totalmente cerrada y el móvil bloqueado, en cualquier navegador, es
 * Web Push real: un servidor manda un push (con claves VAPID) en cada
 * instante programado, y es el sistema operativo (FCM en Android/Chrome,
 * APNs en iOS 16.4+ para PWAs instaladas) quien despierta el SW mediante el
 * evento `push`, exactamente igual que hace WhatsApp. Eso requiere que nuestro
 * backend guarde las `PushSubscription` de cada dispositivo y un Cloud
 * Scheduler que dispare envíos cada pocos minutos durante la ventana horaria.
 * Ver README.md → "Estrategia de notificaciones" para el plan de ampliación.
 *
 * PERSISTENCIA DE CONFIG: un service worker no tiene `localStorage` ni
 * variables globales fiables entre reinicios (el navegador lo mata y
 * recrea). Guardamos la config (URL de la API + intervalo + ventana) en
 * Cache Storage, que sí sobrevive, simulando un pequeño key-value store.
 */

const CONFIG_CACHE = "config-v1";
const CONFIG_KEY = "https://sw.local/__config"; // URL ficticia usada solo como clave

async function saveConfig(config) {
  const cache = await caches.open(CONFIG_CACHE);
  await cache.put(CONFIG_KEY, new Response(JSON.stringify(config)));
}

async function loadConfig() {
  const cache = await caches.open(CONFIG_CACHE);
  const res = await cache.match(CONFIG_KEY);
  return res ? res.json() : null;
}

// ---------------------------------------------------------------------
// Cálculo de horarios en Europe/Madrid sin dependencias externas.
// ---------------------------------------------------------------------

/** Offset (en minutos) de `timeZone` respecto a UTC en el instante `date`. */
function offsetMinutesAt(date, timeZone) {
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
  const get = (type) => parts.find((p) => p.type === type).value;
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

/** Convierte una hora local de pared (Y-M-D hh:mm) en `timeZone` a un Date UTC real. */
function zonedWallTimeToUtc(year, month, day, hour, minute, timeZone) {
  const guess = new Date(Date.UTC(year, month - 1, day, hour, minute));
  const offset = offsetMinutesAt(guess, timeZone);
  // El offset se calcula sobre la fecha "adivinada"; para cambios de hora
  // (DST) esto puede desviarse 1h en el peor caso, aceptable para una alarma
  // de pausas activas (no es un sistema de facturación).
  return new Date(guess.getTime() - offset * 60000);
}

function weekdayInZone(date, timeZone) {
  // 0=domingo ... 6=sábado (formato de Intl) -> lo convertimos a 0=lunes.
  const wd = new Intl.DateTimeFormat("en-US", { timeZone, weekday: "short" }).format(date);
  const map = { Mon: 0, Tue: 1, Wed: 2, Thu: 3, Fri: 4, Sat: 5, Sun: 6 };
  return map[wd];
}

function ymdInZone(date, timeZone) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);
  const get = (type) => Number(parts.find((p) => p.type === type).value);
  return { year: get("year"), month: get("month"), day: get("day") };
}

/**
 * Devuelve los instantes (Date, UTC) en los que debería sonar la alarma
 * durante los próximos `daysAhead` días, respetando días activos y ventana.
 */
function computeUpcomingBreakTimes(config, daysAhead = 2) {
  const { interval_minutes, window_start, window_end, timezone, active_weekdays } = config;
  const [startH, startM] = window_start.split(":").map(Number);
  const [endH, endM] = window_end.split(":").map(Number);
  const weekdays = active_weekdays && active_weekdays.length ? active_weekdays : [0, 1, 2, 3, 4];

  const results = [];
  const now = new Date();
  for (let d = 0; d < daysAhead; d++) {
    const cursor = new Date(now.getTime() + d * 86400000);
    const { year, month, day } = ymdInZone(cursor, timezone);
    if (!weekdays.includes(weekdayInZone(cursor, timezone))) continue;

    const dayStart = zonedWallTimeToUtc(year, month, day, startH, startM, timezone);
    const dayEnd = zonedWallTimeToUtc(year, month, day, endH, endM, timezone);

    for (let t = dayStart.getTime(); t <= dayEnd.getTime(); t += interval_minutes * 60000) {
      results.push(new Date(t));
    }
  }
  return results;
}

// ---------------------------------------------------------------------
// Programación de notificaciones
// ---------------------------------------------------------------------

const TAG_PREFIX = "break-";
const supportsTrigger = () => "showTrigger" in Notification.prototype;

async function clearScheduledNotifications() {
  const all = await self.registration.getNotifications({ includeTriggered: false });
  for (const n of all) {
    if (n.tag && n.tag.startsWith(TAG_PREFIX)) n.close();
  }
}

async function scheduleBreaks() {
  const config = await loadConfig();
  if (!config || !supportsTrigger()) return; // el fallback lo hace la página (ver hook)

  await clearScheduledNotifications();
  const targets = computeUpcomingBreakTimes(config, 2).filter((d) => d.getTime() > Date.now());

  for (const ts of targets) {
    await self.registration.showNotification("Pausa activa 🧘", {
      body: "Levántate, estira 2 min y vuelve. Objetivo: ~8 pausas hoy.",
      tag: `${TAG_PREFIX}${ts.getTime()}`,
      requireInteraction: true,
      data: { ts: ts.getTime(), apiBase: config.apiBase },
      // eslint-disable-next-line no-undef
      showTrigger: new TimestampTrigger(ts.getTime()),
      actions: [
        { action: "done", title: "Hecho ✅" },
        { action: "postpone", title: "Posponer 5 min" },
      ],
    });
  }
}

// ---------------------------------------------------------------------
// Ciclo de vida del SW
// ---------------------------------------------------------------------

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(Promise.all([self.clients.claim(), scheduleBreaks()]));
});

// La app (main thread) manda la config al arrancar o cuando el usuario la
// cambia en Ajustes. Es la única forma fiable de que el SW sepa la URL de
// la API y la ventana horaria, ya que no puede leer `import.meta.env`.
self.addEventListener("message", (event) => {
  if (event.data?.type === "INIT" || event.data?.type === "RESCHEDULE") {
    event.waitUntil(
      saveConfig({ ...event.data.config, apiBase: event.data.apiBase }).then(scheduleBreaks)
    );
  }
});

// Refresco periódico best-effort (solo Chrome/Android, y solo si el usuario
// ha instalado la PWA y la usa con cierta frecuencia: el navegador decide
// cuándo tiene "engagement" suficiente para conceder este permiso).
self.addEventListener("periodicsync", (event) => {
  if (event.tag === "refresh-breaks") {
    event.waitUntil(scheduleBreaks());
  }
});

self.addEventListener("notificationclick", (event) => {
  const { action, notification } = event;
  const { ts, apiBase } = notification.data || {};
  notification.close();

  event.waitUntil(
    (async () => {
      if (!apiBase) return;
      try {
        const created = await fetch(`${apiBase}/breaks`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ scheduled_for: new Date(ts).toISOString() }),
        }).then((r) => r.json());

        if (action === "done") {
          await fetch(`${apiBase}/breaks/${created.id}/done`, { method: "POST" });
        } else if (action === "postpone") {
          await fetch(`${apiBase}/breaks/${created.id}/postpone?minutes=5`, { method: "POST" });
        } else {
          // Click en el cuerpo (no en un botón de acción): abre/enfoca la app.
          const clientsList = await self.clients.matchAll({ type: "window" });
          if (clientsList.length > 0) clientsList[0].focus();
          else await self.clients.openWindow("/");
        }
      } catch (err) {
        // Sin red / API caída: no bloqueamos la UI de notificaciones por esto.
        console.error("[sw] error registrando respuesta de pausa", err);
      } finally {
        await scheduleBreaks();
      }
    })()
  );
});
