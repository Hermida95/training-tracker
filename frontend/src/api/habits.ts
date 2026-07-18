import { api } from "./client";
import type { Habit, HabitLog, HabitWithStatus } from "../types";

export const habitsApi = {
  today: (date?: string) =>
    api.get<HabitWithStatus[]>(`/habits/today${date ? `?date=${date}` : ""}`),
  list: () => api.get<Habit[]>("/habits"),
  upsertLog: (habitId: number, date: string, done: boolean, value?: number | null) =>
    api.post<HabitLog>(`/habits/${habitId}/logs`, { date, done, value: value ?? null }),
};
