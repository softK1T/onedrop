import { api } from '@/lib/api';
import type { TaskRecord } from '@/lib/tasks';

export const NOTE_PAGE_SIZE = 50;
export const MAX_NOTE_TAGS = 10;

export interface NoteRecord {
  id: string;
  title: string | null;
  content: string;
  tags: string[];
  pinned: boolean;
  source_inbox_item_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface NotePage {
  items: NoteRecord[];
  search: string | null;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface NoteDraft {
  title?: string | null;
  content: string;
  tags?: string[];
  pinned?: boolean;
}

export function noteListKey(search: string): string[] {
  return ['notes', search];
}

export function notesPath(search: string): string {
  const query = new URLSearchParams({ limit: String(NOTE_PAGE_SIZE) });
  if (search.trim()) query.set('search', search.trim());
  return `/notes?${query.toString()}`;
}

export function listNotes(search: string): Promise<NotePage> {
  return api.get<NotePage>(notesPath(search));
}

export function createNote(draft: NoteDraft): Promise<NoteRecord> {
  return api.post<NoteRecord>('/notes', draft);
}

export function patchNote(id: string, changes: Partial<NoteDraft>): Promise<NoteRecord> {
  return api.patch<NoteRecord>(`/notes/${id}`, changes);
}

export function pinNote(id: string, pinned: boolean): Promise<NoteRecord> {
  return api.post<NoteRecord>(`/notes/${id}/pin`, { pinned });
}

export function convertNoteToTask(
  id: string,
  options: { due_at?: string | null; keep_note?: boolean } = {},
): Promise<TaskRecord> {
  return api.post<TaskRecord>(`/notes/${id}/convert-to-task`, {
    due_at: options.due_at ?? null,
    keep_note: options.keep_note ?? true,
  });
}

export function deleteNote(id: string): Promise<void> {
  return api.del<void>(`/notes/${id}`);
}

export function parseTags(value: string): string[] {
  return value
    .split(',')
    .map((tag) => tag.trim())
    .filter((tag) => tag.length > 0)
    .slice(0, MAX_NOTE_TAGS);
}
