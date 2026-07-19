// Tipos espejo de los schemas Pydantic del backend (app/schemas/*.py).
// Se mantienen a mano en vez de generarlos porque el proyecto es pequeño;
// si creciera, valdría la pena generar esto desde /openapi.json.

export type HabitValueType = "boolean" | "numeric";

export interface Habit {
  id: number;
  key: string;
  name: string;
  value_type: HabitValueType;
  target_value: number | null;
  unit: string | null;
  active_days: number[]; // 0=Lunes ... 6=Domingo
  sort_order: number;
  created_at: string;
}

export interface HabitWithStatus extends Habit {
  due_today: boolean;
  done_today: boolean;
  value_today: number | null;
  current_streak: number;
}

export type DayScoreTier = "perfect" | "great" | "half" | "missed" | "rest";

export interface DayScore {
  date: string;
  due_count: number;
  done_count: number;
  completion_rate: number | null;
  points: number;
  tier: DayScoreTier;
  streak: number; // días consecutivos con >=75% del checklist
}

export interface HabitLog {
  id: number;
  habit_id: number;
  date: string;
  done: boolean;
  value: number | null;
}

export type WorkoutType = "GYM1" | "GYM2" | "GYM3" | "RUNNING" | "CUSTOM";

export interface ExerciseTemplate {
  id: number;
  workout_type: WorkoutType;
  name: string;
  order: number;
  target_sets: number;
  target_reps: string;
  base_weight_kg: number | null;
}

export interface WorkoutSet {
  id?: number;
  set_number: number;
  weight_kg: number | null;
  reps: number | null;
  rir?: number | null;
}

export interface WorkoutExercise {
  id?: number;
  name: string;
  order: number;
  exercise_template_id: number | null;
  sets: WorkoutSet[];
}

export interface WorkoutSession {
  id: number;
  date: string;
  workout_type: WorkoutType;
  cycle_week: number;
  notes: string | null;
  running_minutes: number | null;
  running_feeling: number | null;
  exercises: WorkoutExercise[];
}

export interface SetComparison {
  set_number: number;
  previous_weight_kg: number | null;
  previous_reps: number | null;
  current_weight_kg: number | null;
  current_reps: number | null;
  weight_delta_kg: number | null;
  reps_delta: number | null;
}

export interface SessionComparison {
  current_session_id: number;
  previous_session_id: number | null;
  previous_date: string | null;
  exercises: { name: string; sets: SetComparison[] }[];
}

export interface PeriodizationInfo {
  cycle_week: number;
  label: string;
  rir_target: string;
  weight_adjustment_kg: number;
  set_adjustment: number;
  description: string;
}

export interface BodyMetric {
  id: number;
  date: string;
  weight_kg: number | null;
  waist_cm: number | null;
}

export interface WeeklyAveragePoint {
  week_start: string;
  avg_weight_kg: number | null;
  avg_waist_cm: number | null;
  sample_count: number;
}

export type BreakStatus = "pending" | "done" | "postponed";

export interface BreakEvent {
  id: number;
  scheduled_for: string;
  status: BreakStatus;
  responded_at: string | null;
  postponed_from_id: number | null;
}

export interface BreakConfig {
  interval_minutes: number;
  window_start: string;
  window_end: string;
  active_weekdays: number[];
  timezone: string;
  daily_target: number;
}

export interface MonthlyStats {
  year: number;
  month: number;
  sessions_completed: number;
  sessions_by_type: Record<string, number>;
  avg_steps: number | null;
  steps_goal_days: number;
  weight_start_kg: number | null;
  weight_end_kg: number | null;
  weight_trend_kg: number | null;
  waist_start_cm: number | null;
  waist_end_cm: number | null;
  waist_trend_cm: number | null;
  breaks_done: number;
  breaks_total: number;
  habit_completion_rate: number;
  points_total: number;
  perfect_days: number;
}
