import { useEffect, useRef } from "react";
import { API_BASE_URL, getToken } from "../api/client";
import { breaksApi } from "../api/breaks";
import { computeNextBreakTime } from "../notifications/scheduleMath";
import type { BreakConfig } from "../types";

const MAX_TIMEOUT_MS = 2_147_483_647; // límite de setTimeout (~24.8 días)

/**
 * Registra el service worker y arranca la programación de la alarma
 * antisedentarismo. Ver public/sw.js para la explicación completa de la
 * estrategia (Notification Triggers + fallback). Este hook:
 *  1) Registra/actualiza el SW y le pasa la config actual (INIT).
 *  2) Si el navegador no soporta Notification Triggers, mantiene un
 *     `setTimeout` en la página como red de seguridad mientras esté abierta.
 */
export function useNotificationScheduler(enabled: boolean) {
  const fallbackTimer = useRef<number | null>(null);

  useEffect(() => {
    if (!enabled || !("serviceWorker" in navigator) || !("Notification" in window)) return;

    let cancelled = false;

    async function init() {
      const registration = await navigator.serviceWorker.register("/sw.js");
      await navigator.serviceWorker.ready;

      if (Notification.permission === "default") {
        await Notification.requestPermission();
      }
      if (Notification.permission !== "granted" || cancelled) return;

      const config = await breaksApi.getConfig();
      if (cancelled) return;

      registration.active?.postMessage({
        type: "INIT",
        apiBase: API_BASE_URL,
        token: getToken(),
        config,
      });

      const supportsTrigger = "showTrigger" in Notification.prototype;
      if (!supportsTrigger) {
        scheduleFallback(registration, config);
      }
    }

    function scheduleFallback(registration: ServiceWorkerRegistration, config: BreakConfig) {
      const next = computeNextBreakTime(config);
      if (!next) return;

      const delay = Math.min(next.getTime() - Date.now(), MAX_TIMEOUT_MS);
      fallbackTimer.current = window.setTimeout(async () => {
        await registration.showNotification("Pausa activa 🧘", {
          body: "Levántate, estira 2 min y vuelve. Objetivo: ~8 pausas hoy.",
          tag: `break-fallback-${next.getTime()}`,
          requireInteraction: true,
          data: { ts: next.getTime(), apiBase: API_BASE_URL },
          actions: [
            { action: "done", title: "Hecho ✅" },
            { action: "postpone", title: "Posponer 5 min" },
          ],
        } as NotificationOptions);
        // Vuelve a programar la siguiente mientras la app siga abierta.
        scheduleFallback(registration, config);
      }, delay);
    }

    init();

    return () => {
      cancelled = true;
      if (fallbackTimer.current !== null) window.clearTimeout(fallbackTimer.current);
    };
  }, [enabled]);
}

/** Llamar tras cambiar la config en Ajustes para que el SW reprograme al momento. */
export async function pushBreakConfigToServiceWorker(config: BreakConfig) {
  if (!("serviceWorker" in navigator)) return;
  const registration = await navigator.serviceWorker.ready;
  registration.active?.postMessage({
    type: "RESCHEDULE",
    apiBase: API_BASE_URL,
    token: getToken(),
    config,
  });
}
