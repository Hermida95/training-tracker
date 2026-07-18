import { api, API_BASE_URL } from "./client";
import type { MonthlyStats } from "../types";

export const statsApi = {
  monthly: (year?: number, month?: number) => {
    const qs = new URLSearchParams();
    if (year) qs.set("year", String(year));
    if (month) qs.set("month", String(month));
    const suffix = qs.toString() ? `?${qs}` : "";
    return api.get<MonthlyStats>(`/stats/monthly${suffix}`);
  },
  exportTextUrl: (year: number, month: number) =>
    `${API_BASE_URL}/export?year=${year}&month=${month}&format=text`,
  exportJsonUrl: (year: number, month: number) =>
    `${API_BASE_URL}/export?year=${year}&month=${month}&format=json`,
};
