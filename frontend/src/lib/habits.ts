import { api } from '@/lib/api';

export const MEASUREMENT_TYPES = ['boolean', 'numeric'] as const;
export type MeasurementType = (typeof MEASUREMENT_TYPES)[number];
/** ISO weekday numbers, exactly what the backend validator accepts. */
export const WEEKDAYS = [1, 2, 3, 4, 5, 6, 7] as const;
export const HABIT_PAGE_SIZE = 50;
export const PROGRESS_DAYS = 30;

export interface HabitRecord {
  id: string;
  name: string;
  measurement_type: string;
  target_value: number | null;
  unit: string | null;
  active: boolean;
  reminder_hour: number | null;
  source_inbox_item_id: string | null;
  created_at: string;
}

export interface HabitPage {
  items: HabitRecord[];
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface HabitProgress {
  habit_id: string;
  name: string;
  period_start: string;
  period_end: string;
  scheduled_days: number[];
  expected: number;
  completed: number;
  missed: number;
  percent: number | null;
}

export interface HabitDraft {
  name: string;
  measurement_type: MeasurementType;
  target_value?: number | null;
  unit?: string | null;
  schedule_days?: number[];
  reminder_hour?: number | null;
}

export interface HabitChanges {
  name?: string;
  target_value?: number | null;
  unit?: string | null;
  schedule_days?: number[];
  reminder_hour?: number | null;
  active?: boolean;
}

export function habitListKey(includeInactive: boolean): (string | boolean)[] {
  return ['habits', includeInactive];
}

export function habitProgressKey(id: string): string[] {
  return ['habits', 'progress', id];
}

export function habitsPath(includeInactive: boolean): string {
  const query = new URLSearchParams({ limit: String(HABIT_PAGE_SIZE) });
  if (includeInactive) query.set('include_inactive', 'true');
  return `/habits?${query.toString()}`;
}

export function listHabits(includeInactive: boolean): Promise<HabitPage> {
  return api.get<HabitPage>(habitsPath(includeInactive));
}

export function createHabit(draft: HabitDraft): Promise<HabitRecord> {
  return api.post<HabitRecord>('/habits', draft);
}

export function patchHabit(id: string, changes: HabitChanges): Promise<HabitRecord> {
  return api.patch<HabitRecord>(`/habits/${id}`, changes);
}

export function disableHabit(id: string): Promise<HabitRecord> {
  return api.post<HabitRecord>(`/habits/${id}/disable`);
}

export function logHabit(id: string, value: number): Promise<unknown> {
  return api.post(`/habits/${id}/log`, { value });
}

export function loadProgress(id: string): Promise<HabitProgress> {
  return api.get<HabitProgress>(`/habits/${id}/progress?days=${PROGRESS_DAYS}`);
}

export function deleteHabit(id: string): Promise<void> {
  return api.del<void>(`/habits/${id}`);
}

export function toggleDay(days: number[], day: number): number[] {
  return days.includes(day)
    ? days.filter((entry) => entry !== day)
    : [...days, day].sort((left, right) => left - right);
}

export function checkInValue(habit: HabitRecord): number {
  if (habit.measurement_type !== 'numeric') return 1;
  return habit.target_value === null || habit.target_value === 0 ? 1 : habit.target_value;
}
