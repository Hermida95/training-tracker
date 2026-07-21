import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { authApi } from "../api/auth";
import { clearToken, getToken, setToken } from "../api/client";
import type { User } from "../types";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, inviteCode: string | null) => Promise<void>;
  resetPassword: (email: string, recoveryCode: string, newPassword: string) => Promise<void>;
  refreshUser: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Al arrancar, si hay token guardado se valida contra /auth/me.
  // Si es inválido, el cliente API ya se encarga de limpiarlo (401).
  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    authApi
      .me()
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setLoading(false));
  }, []);

  const login = async (email: string, password: string) => {
    const res = await authApi.login(email, password);
    setToken(res.access_token);
    setUser(res.user);
  };

  const register = async (email: string, password: string, inviteCode: string | null) => {
    const res = await authApi.register(email, password, inviteCode);
    setToken(res.access_token);
    setUser(res.user);
  };

  const resetPassword = async (email: string, recoveryCode: string, newPassword: string) => {
    const res = await authApi.resetPassword(email, recoveryCode, newPassword);
    setToken(res.access_token);
    setUser(res.user);
  };

  // Para refrescar flags del usuario (ej. has_recovery_code tras generarlo).
  const refreshUser = async () => {
    setUser(await authApi.me());
  };

  const logout = () => {
    clearToken();
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{ user, loading, login, register, resetPassword, refreshUser, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// Patrón estándar de contexto + hook en el mismo fichero. El warning de
// react-refresh solo afecta al hot-reload en desarrollo (recarga completa en
// vez de parcial al editar ESTE fichero), no al build de producción.
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return ctx;
}
