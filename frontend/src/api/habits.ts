import { api } from "./client";
import type { Habit, HabitLog, HabitValueType, HabitWithStatus } from "../types";

export interface HabitCreatePayload {
  key: string;
  name: string;
  value_type: HabitValueType;
  target_value: number | null;
  unit: string | null;
  active_days: number[];
  sort_order?: number;
}

export const habitsApi = {
  today: (date?: string) =>
    api.get<HabitWithStatus[]>(`/habits/today${date ? `?date=${date}` : ""}`),
  list: () => api.get<Habit[]>("/habits"),
  create: (payload: HabitCreatePayload) => api.post<Habit>("/habits", payload),
  update: (habitId: number, patch: Partial<Pick<Habit, "name" | "target_value" | "unit" | "active_days" | "sort_order">>) =>
    api.patch<Habit>(`/habits/${habitId}`, patch),
  remove: (habitId: number) => api.delete<void>(`/habits/${habitId}`),
  upsertLog: (habitId: number, date: string, done: boolean, value?: number | null) =>
    api.post<HabitLog>(`/habits/${habitId}/logs`, { date, done, value: value ?? null }),
};
