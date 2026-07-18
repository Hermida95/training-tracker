import { api } from "./client";
import type {
  ExerciseTemplate,
  PeriodizationInfo,
  SessionComparison,
  WorkoutSession,
  WorkoutType,
} from "../types";

export const workoutsApi = {
  templates: (workoutType?: WorkoutType) =>
    api.get<ExerciseTemplate[]>(
      `/workouts/templates${workoutType ? `?workout_type=${workoutType}` : ""}`
    ),
  periodization: (date?: string) =>
    api.get<PeriodizationInfo>(`/workouts/periodization${date ? `?date=${date}` : ""}`),
  list: (params: { workout_type?: WorkoutType; limit?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.workout_type) qs.set("workout_type", params.workout_type);
    if (params.limit) qs.set("limit", String(params.limit));
    const suffix = qs.toString() ? `?${qs}` : "";
    return api.get<WorkoutSession[]>(`/workouts${suffix}`);
  },
  get: (id: number) => api.get<WorkoutSession>(`/workouts/${id}`),
  create: (data: {
    date: string;
    workout_type: WorkoutType;
    notes?: string | null;
    running_minutes?: number | null;
    running_feeling?: number | null;
    exercises: {
      name: string;
      order: number;
      exercise_template_id: number | null;
      sets: { set_number: number; weight_kg: number | null; reps: number | null; rir?: number | null }[];
    }[];
  }) => api.post<WorkoutSession>("/workouts", data),
  comparison: (id: number) => api.get<SessionComparison>(`/workouts/${id}/comparison`),
};
