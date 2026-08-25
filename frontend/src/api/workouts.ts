import { api } from "./client";
import type {
  ExerciseTemplate,
  PeriodizationInfo,
  SessionComparison,
  WorkoutSession,
  WorkoutType,
} from "../types";

export interface SessionPayload {
  date: string;
  workout_type: WorkoutType;
  completed?: boolean;
  notes?: string | null;
  running_minutes?: number | null;
  running_feeling?: number | null;
  exercises: {
    name: string;
    order: number;
    exercise_template_id: number | null;
    sets: { set_number: number; weight_kg: number | null; reps: number | null; rir?: number | null }[];
  }[];
}

export interface TemplatePayload {
  workout_type: WorkoutType;
  name: string;
  target_sets?: number;
  target_reps?: string;
  base_weight_kg?: number | null;
}

export const workoutsApi = {
  templates: (workoutType?: WorkoutType) =>
    api.get<ExerciseTemplate[]>(
      `/workouts/templates${workoutType ? `?workout_type=${workoutType}` : ""}`
    ),
  createTemplate: (data: TemplatePayload) =>
    api.post<ExerciseTemplate>("/workouts/templates", data),
  updateTemplate: (id: number, data: Partial<TemplatePayload>) =>
    api.patch<ExerciseTemplate>(`/workouts/templates/${id}`, data),
  deleteTemplate: (id: number) => api.delete<void>(`/workouts/templates/${id}`),
  periodization: (date?: string) =>
    api.get<PeriodizationInfo>(`/workouts/periodization${date ? `?date=${date}` : ""}`),
  list: (params: { workout_type?: WorkoutType; start?: string; end?: string; limit?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.workout_type) qs.set("workout_type", params.workout_type);
    if (params.start) qs.set("start", params.start);
    if (params.end) qs.set("end", params.end);
    if (params.limit) qs.set("limit", String(params.limit));
    const suffix = qs.toString() ? `?${qs}` : "";
    return api.get<WorkoutSession[]>(`/workouts${suffix}`);
  },
  get: (id: number) => api.get<WorkoutSession>(`/workouts/${id}`),
  create: (data: SessionPayload) => api.post<WorkoutSession>("/workouts", data),
  update: (id: number, data: SessionPayload) => api.put<WorkoutSession>(`/workouts/${id}`, data),
  remove: (id: number) => api.delete<void>(`/workouts/${id}`),
  comparison: (id: number) => api.get<SessionComparison>(`/workouts/${id}/comparison`),
};
