import { api } from "./client";
import type { InviteCode, TokenResponse, User } from "../types";

export const authApi = {
  register: (email: string, password: string, inviteCode: string | null) =>
    api.post<TokenResponse>("/auth/register", {
      email,
      password,
      invite_code: inviteCode,
    }),
  login: (email: string, password: string) =>
    api.post<TokenResponse>("/auth/login", { email, password }),
  me: () => api.get<User>("/auth/me"),
  // El código de recuperación en claro solo viaja en esta respuesta: hay que
  // mostrarlo al usuario inmediatamente y pedirle que lo guarde.
  generateRecoveryCode: () =>
    api.post<{ recovery_code: string }>("/auth/recovery-code"),
  resetPassword: (email: string, recoveryCode: string, newPassword: string) =>
    api.post<TokenResponse>("/auth/reset-password", {
      email,
      recovery_code: recoveryCode,
      new_password: newPassword,
    }),
};

export const invitesApi = {
  list: () => api.get<InviteCode[]>("/invites"),
  create: () => api.post<InviteCode>("/invites"),
};
