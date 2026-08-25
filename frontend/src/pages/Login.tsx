import { useState } from "react";
import type { FormEvent } from "react";
import { MountainIcon } from "../components/icons";
import { useAuth } from "../auth/AuthContext";

type Mode = "login" | "register" | "reset";

const TITLES: Record<Mode, string> = {
  login: "Entrar",
  register: "Crear cuenta",
  reset: "Recuperar contraseña",
};

export default function Login() {
  const { login, register, resetPassword } = useAuth();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [recoveryCode, setRecoveryCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const switchMode = (next: Mode) => {
    setMode(next);
    setError(null);
    setPassword("");
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "login") {
        await login(email, password);
      } else if (mode === "register") {
        await register(email, password, inviteCode.trim() || null);
      } else {
        await resetPassword(email, recoveryCode, password);
      }
    } catch (err) {
      const raw = err instanceof Error ? err.message : "";
      if (mode === "register" && raw.includes("409")) {
        setError("Ya existe una cuenta con ese email.");
      } else if (mode === "register" && raw.includes("403")) {
        setError("Código de invitación no válido. Pídeselo a quien te invitó.");
      } else if (mode === "register") {
        setError("No se pudo crear la cuenta. La contraseña necesita 8+ caracteres.");
      } else if (mode === "reset") {
        setError("Email o código de recuperación incorrectos.");
      } else {
        setError("Email o contraseña incorrectos.");
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-screen">
      <span className="topo-texture" aria-hidden="true" />
      <div className="login-brand">
        <span className="login-logo">
          <MountainIcon size={32} strokeWidth={1.5} />
        </span>
        <h1>CIMA</h1>
        <p>Tu entreno, tu cima.</p>
      </div>

      <form className="card login-card" onSubmit={submit}>
        <h2>{TITLES[mode]}</h2>

        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        {mode === "register" && (
          <>
            <label htmlFor="invite" style={{ marginTop: 12, display: "block" }}>
              Código de invitación
            </label>
            <input
              id="invite"
              type="text"
              placeholder="XXXX-XXXX"
              autoComplete="off"
              value={inviteCode}
              onChange={(e) => setInviteCode(e.target.value)}
            />
          </>
        )}

        {mode === "reset" && (
          <>
            <label htmlFor="recovery" style={{ marginTop: 12, display: "block" }}>
              Código de recuperación
            </label>
            <input
              id="recovery"
              type="text"
              placeholder="XXXX-XXXX-XXXX"
              autoComplete="off"
              required
              value={recoveryCode}
              onChange={(e) => setRecoveryCode(e.target.value)}
            />
          </>
        )}

        <label htmlFor="password" style={{ marginTop: 12, display: "block" }}>
          {mode === "reset" ? "Nueva contraseña" : "Contraseña"}
        </label>
        <input
          id="password"
          type="password"
          autoComplete={mode === "login" ? "current-password" : "new-password"}
          minLength={8}
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        {error && <p className="login-error">{error}</p>}

        <button className="primary big" type="submit" disabled={busy} style={{ marginTop: 16 }}>
          {busy ? "Un momento…" : TITLES[mode]}
        </button>

        {mode === "login" ? (
          <>
            <button
              type="button"
              className="ghost login-switch"
              onClick={() => switchMode("register")}
            >
              ¿Tienes una invitación? Crea tu cuenta
            </button>
            <button
              type="button"
              className="ghost login-switch"
              onClick={() => switchMode("reset")}
            >
              ¿Olvidaste la contraseña?
            </button>
          </>
        ) : (
          <button type="button" className="ghost login-switch" onClick={() => switchMode("login")}>
            ¿Ya tienes cuenta? Entra
          </button>
        )}
      </form>
    </div>
  );
}
