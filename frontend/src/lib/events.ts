import { api } from '@/lib/api';

export const EVENT_PERIODS = ['day', 'week'] as const;
export type EventPeriod = (typeof EVENT_PERIODS)[number];
export const EVENT_PAGE_SIZE = 50;

export interface EventRecord {
  id: string;
  title: string;
  starts_at: string;
  ends_at: string | null;
  location: string | null;
  description: string | null;
  status: string;
  source_inbox_item_id: string | null;
  created_at: string;
}

export interface EventPage {
  items: EventRecord[];
  range: EventPeriod;
  anchor_date: string;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface EventWithConflicts {
  event: EventRecord;
  conflicts: string[];
}

export interface EventDraft {
  title: string;
  starts_at: string;
  ends_at?: string | null;
  location?: string | null;
  description?: string | null;
}

export interface EventChanges {
  title?: string;
  starts_at?: string;
  ends_at?: string | null;
  location?: string | null;
  status?: 'planned' | 'done' | 'cancelled';
}

export function eventListKey(period: EventPeriod, anchor: string): string[] {
  return ['events', period, anchor];
}

export function eventsPath(period: EventPeriod, anchor: string): string {
  const query = new URLSearchParams({ period, limit: String(EVENT_PAGE_SIZE) });
  if (anchor) query.set('date', anchor);
  return `/events?${query.toString()}`;
}

export function listEvents(period: EventPeriod, anchor: string): Promise<EventPage> {
  return api.get<EventPage>(eventsPath(period, anchor));
}

export function createEvent(draft: EventDraft): Promise<EventWithConflicts> {
  return api.post<EventWithConflicts>('/events', draft);
}

export function patchEvent(id: string, changes: EventChanges): Promise<EventWithConflicts> {
  return api.patch<EventWithConflicts>(`/events/${id}`, changes);
}

export function deleteEvent(id: string): Promise<void> {
  return api.del<void>(`/events/${id}`);
}
