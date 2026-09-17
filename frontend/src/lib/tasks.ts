import { api } from '@/lib/api';

export const TASK_FILTERS = ['today', 'upcoming', 'no_date', 'completed', 'all'] as const;
export type TaskFilter = (typeof TASK_FILTERS)[number];
export const TASK_PRIORITIES = ['low', 'normal', 'high'] as const;
export type TaskPriority = (typeof TASK_PRIORITIES)[number];
export const TASK_PAGE_SIZE = 50;

export interface TaskRecord {
  id: string;
  title: string;
  description: string | null;
  due_at: string | null;
  priority: string;
  status: string;
  category: string | null;
  reminder_at: string | null;
  completed_at: string | null;
  source_inbox_item_id: string | null;
  created_at: string;
}

export interface TaskPage {
  items: TaskRecord[];
  limit: number;
  offset: number;
  has_more: boolean;
  filter: string;
}

export interface TaskDraft {
  title: string;
  due_at?: string | null;
  priority?: TaskPriority;
  description?: string | null;
  reminder_at?: string | null;
}

export function taskListKey(filter: TaskFilter): (string | TaskFilter)[] {
  return ['tasks', filter];
}

export function listTasks(filter: TaskFilter): Promise<TaskPage> {
  return api.get<TaskPage>(`/tasks?filter=${filter}&limit=${TASK_PAGE_SIZE}`);
}

export function createTask(draft: TaskDraft): Promise<TaskRecord> {
  return api.post<TaskRecord>('/tasks', draft);
}

export function patchTask(id: string, changes: Partial<TaskDraft>): Promise<TaskRecord> {
  return api.patch<TaskRecord>(`/tasks/${id}`, changes);
}

export function completeTask(id: string): Promise<TaskRecord> {
  return api.post<TaskRecord>(`/tasks/${id}/complete`);
}

export function deleteTask(id: string): Promise<void> {
  return api.del<void>(`/tasks/${id}`);
}

export function localDateTimeToIso(value: string): string | null {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed.toISOString();
}
