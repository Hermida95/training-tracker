import { api } from "./client";
import type { PlannedWorkout } from "../types";

export const plannedApi = {
  today: (date: string) =>
    api.get<PlannedWorkout | null>(`/planned/today?date=${date}`),
  week: (start: string, end: string) =>
    api.get<PlannedWorkout[]>(`/planned?start=${start}&end=${end}`),
};
