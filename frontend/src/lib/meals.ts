import { api } from '@/lib/api';

export const MEAL_TYPES = ['breakfast', 'lunch', 'dinner', 'snack'] as const;
export type MealType = (typeof MEAL_TYPES)[number];
export const MEAL_PAGE_SIZE = 50;

export interface MealRecord {
  id: string;
  title: string;
  meal_type: string;
  eaten_at: string;
  calories: number | null;
  protein: number | null;
  fat: number | null;
  carbohydrates: number | null;
  estimated: boolean;
  source_inbox_item_id: string | null;
  created_at: string;
}

export interface MealPage {
  items: MealRecord[];
  day: string;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface DailyNutrition {
  day: string;
  meals_count: number;
  calories: number;
  protein: number;
  fat: number;
  carbohydrates: number;
  contains_estimates: boolean;
  disclaimer: string;
}

export interface MealDraft {
  title: string;
  meal_type: MealType;
  calories?: number | null;
  protein?: number | null;
  fat?: number | null;
  carbohydrates?: number | null;
  estimated?: boolean;
}

export interface MealChanges {
  title?: string;
  meal_type?: MealType;
  calories?: number | null;
  protein?: number | null;
  fat?: number | null;
  carbohydrates?: number | null;
}

export function mealListKey(day: string): string[] {
  return ['meals', day];
}

export function mealDailyKey(day: string): string[] {
  return ['meals', 'daily', day];
}

export function mealsPath(day: string): string {
  const query = new URLSearchParams({ limit: String(MEAL_PAGE_SIZE) });
  if (day) query.set('day', day);
  return `/meals?${query.toString()}`;
}

export function dailyPath(day: string): string {
  return day ? `/meals/daily?day=${day}` : '/meals/daily';
}

export function listMeals(day: string): Promise<MealPage> {
  return api.get<MealPage>(mealsPath(day));
}

export function loadDaily(day: string): Promise<DailyNutrition> {
  return api.get<DailyNutrition>(dailyPath(day));
}

export function createMeal(draft: MealDraft): Promise<MealRecord> {
  return api.post<MealRecord>('/meals', draft);
}

export function patchMeal(id: string, changes: MealChanges): Promise<MealRecord> {
  return api.patch<MealRecord>(`/meals/${id}`, changes);
}

export function deleteMeal(id: string): Promise<void> {
  return api.del<void>(`/meals/${id}`);
}

/** Empty stays empty: an unknown macro is null, never a silent zero. */
export function optionalNumber(value: string, max: number): number | null {
  if (!value.trim()) return null;
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 0 || parsed > max) return null;
  return Math.round(parsed);
}
