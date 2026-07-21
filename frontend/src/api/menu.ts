import { api, API_BASE_URL, getToken } from "./client";
import type { MenuDocument } from "../types";

export const menuApi = {
  list: () => api.get<MenuDocument[]>("/menu"),
  upload: (title: string, file: File | null, textContent: string | null) => {
    const form = new FormData();
    form.append("title", title);
    if (file) form.append("file", file);
    if (textContent) form.append("text_content", textContent);
    return api.post<MenuDocument>("/menu", form);
  },
  remove: (id: number) => api.delete<void>(`/menu/${id}`),

  // Los <img src> no pueden mandar el header Authorization, así que el fichero
  // se baja con fetch autenticado y se muestra vía object URL (blob:).
  // El llamador debe hacer URL.revokeObjectURL cuando deje de usarla.
  fetchFileUrl: async (id: number): Promise<string> => {
    const res = await fetch(`${API_BASE_URL}/menu/${id}/file`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    if (!res.ok) throw new Error(`No se pudo cargar el fichero (${res.status})`);
    return URL.createObjectURL(await res.blob());
  },
};
