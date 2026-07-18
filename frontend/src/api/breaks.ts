import { api } from "./client";
import type { BreakConfig, BreakEvent } from "../types";

export const breaksApi = {
  getConfig: () => api.get<BreakConfig>("/breaks/config"),
  updateConfig: (config: BreakConfig) => api.put<BreakConfig>("/breaks/config", config),
  list: (start?: string, end?: string) => {
    const qs = new URLSearchParams();
    if (start) qs.set("start", start);
    if (end) qs.set("end", end);
    const suffix = qs.toString() ? `?${qs}` : "";
    return api.get<BreakEvent[]>(`/breaks${suffix}`);
  },
};
