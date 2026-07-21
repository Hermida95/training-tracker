import { useEffect, useState } from "react";
import { authApi } from "../api/auth";
import { breaksApi } from "../api/breaks";
import { useAuth } from "../auth/AuthContext";
import { HabitManager } from "../components/HabitManager";
import { InviteManager } from "../components/InviteManager";
import { pushBreakConfigToServiceWorker } from "../hooks/useNotificationScheduler";
import type { BreakConfig } from "../types";

export default function Settings() {
  const { user, logout, refreshUser } = useAuth();
  const [recoveryCode, setRecoveryCode] = useState<string | null>(null);

  const generateRecovery = async () => {
    const res = await authApi.generateRecoveryCode();
    setRecoveryCode(res.recovery_code);
    await refreshUser();
  };
  const [config, setConfig] = useState<BreakConfig | null>(null);
  const [permission, setPermission] = useState<NotificationPermission>(
    "Notification" in window ? Notification.permission : "denied"
  );
  const [saved, setSaved] = useState(false);
  const supportsTrigger =
    "Notification" in window && "showTrigger" in Notification.prototype;

  useEffect(() => {
    breaksApi.getConfig().then(setConfig);
  }, []);

  const requestPermission = async () => {
    const result = await Notification.requestPermission();
    setPermission(result);
  };

  const save = async () => {
    if (!config) return;
    const updated = await breaksApi.updateConfig(config);
    setConfig(updated);
    await pushBreakConfigToServiceWorker(updated);
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  };

  return (
    <div>
      <div className="top-bar">
        <h1>Ajustes</h1>
      </div>
      <main>
        <div className="card">
          <h2>Notificaciones</h2>
          <p>
            Estado del permiso: <strong>{permission}</strong>
          </p>
          {permission !== "granted" && (
            <button className="primary" onClick={requestPermission}>
              Activar notificaciones
            </button>
          )}
          <p style={{ marginTop: 12, fontSize: "0.82rem" }}>
            {supportsTrigger
              ? "Este navegador soporta notificaciones programadas exactas (funcionan con la app cerrada y el móvil bloqueado)."
              : "Este navegador no soporta notificaciones programadas exactas: la alarma solo sonará mientras la app esté abierta en segundo plano reciente. Ver README para la alternativa con Web Push."}
          </p>
        </div>

        {config && (
          <div className="card">
            <h2>Alarma antisedentarismo</h2>
            <label>Intervalo (minutos)</label>
            <input
              type="number"
              min={5}
              max={120}
              value={config.interval_minutes}
              onChange={(e) => setConfig({ ...config, interval_minutes: Number(e.target.value) })}
            />
            <label style={{ marginTop: 10, display: "block" }}>Desde</label>
            <input
              type="time"
              value={config.window_start}
              onChange={(e) => setConfig({ ...config, window_start: e.target.value })}
            />
            <label style={{ marginTop: 10, display: "block" }}>Hasta</label>
            <input
              type="time"
              value={config.window_end}
              onChange={(e) => setConfig({ ...config, window_end: e.target.value })}
            />
            <p style={{ marginTop: 8 }}>
              Activo: Lunes a Viernes · Zona horaria: {config.timezone}
            </p>
            <button className="primary big" style={{ marginTop: 12 }} onClick={save}>
              {saved ? "Guardado ✓" : "Guardar"}
            </button>
          </div>
        )}

        <HabitManager />

        <div className="card">
          <h2>Instalar la app</h2>
          <p>
            Desde el navegador del móvil: menú → "Añadir a pantalla de inicio". Así la app
            corre en modo standalone y las notificaciones funcionan igual que una app nativa.
          </p>
        </div>

        {user?.is_admin && <InviteManager />}

        <div className="card">
          <h2>Cuenta</h2>
          <p>
            Sesión iniciada como <strong>{user?.email}</strong>
          </p>

          <h2 style={{ marginTop: 16 }}>Recuperación de contraseña</h2>
          {recoveryCode ? (
            <div className="recovery-reveal">
              <code className="invite-code">{recoveryCode}</code>
              <p style={{ marginTop: 8, fontSize: "0.82rem" }}>
                Guárdalo ahora (gestor de contraseñas, nota segura…): <strong>no se volverá a
                mostrar</strong>. Si olvidas la contraseña, lo usarás junto a tu email para poner
                una nueva. Es de un solo uso.
              </p>
            </div>
          ) : (
            <p style={{ fontSize: "0.82rem" }}>
              {user?.has_recovery_code
                ? "Tienes un código de recuperación activo. Generar uno nuevo invalida el anterior."
                : "Sin código de recuperación: si olvidas la contraseña no podrás recuperar la cuenta. Genera uno y guárdalo a buen recaudo."}
            </p>
          )}
          <button style={{ width: "100%", marginBottom: 8 }} onClick={generateRecovery}>
            {user?.has_recovery_code ? "Regenerar código" : "Generar código de recuperación"}
          </button>

          <button className="danger" style={{ width: "100%" }} onClick={logout}>
            Cerrar sesión
          </button>
        </div>
      </main>
    </div>
  );
}
