import { api } from "./client";
import type { BodyMetric, WeeklyAveragePoint } from "../types";

export const bodyMetricsApi = {
  list: (start?: string, end?: string) => {
    const qs = new URLSearchParams();
    if (start) qs.set("start", start);
    if (end) qs.set("end", end);
    const suffix = qs.toString() ? `?${qs}` : "";
    return api.get<BodyMetric[]>(`/body-metrics${suffix}`);
  },
  upsert: (date: string, weight_kg?: number | null, waist_cm?: number | null) =>
    api.post<BodyMetric>("/body-metrics", { date, weight_kg, waist_cm }),
  weeklyAverage: () => api.get<WeeklyAveragePoint[]>("/body-metrics/weekly-average"),
};
