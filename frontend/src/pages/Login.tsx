import { useState } from "react";
import type { FormEvent } from "react";
import { BarbellIcon } from "../components/icons";
import { useAuth } from "../auth/AuthContext";

type Mode = "login" | "register";

export default function Login() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password);
    } catch (err) {
      const raw = err instanceof Error ? err.message : "";
      if (raw.includes("409")) setError("Ya existe una cuenta con ese email.");
      else if (mode === "login") setError("Email o contraseña incorrectos.");
      else setError("No se pudo crear la cuenta. La contraseña necesita 8+ caracteres.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-screen">
      <div className="login-brand">
        <span className="login-logo">
          <BarbellIcon size={30} strokeWidth={1.4} />
        </span>
        <h1>Entreno &amp; Hábitos</h1>
        <p>Tu programa, tus datos.</p>
      </div>

      <form className="card login-card" onSubmit={submit}>
        <h2>{mode === "login" ? "Entrar" : "Crear cuenta"}</h2>

        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <label htmlFor="password" style={{ marginTop: 12, display: "block" }}>
          Contraseña
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
          {busy ? "Un momento…" : mode === "login" ? "Entrar" : "Crear cuenta"}
        </button>

        <button
          type="button"
          className="ghost login-switch"
          onClick={() => {
            setMode(mode === "login" ? "register" : "login");
            setError(null);
          }}
        >
          {mode === "login" ? "¿Primera vez? Crea tu cuenta" : "¿Ya tienes cuenta? Entra"}
        </button>
      </form>
    </div>
  );
}
