import { api } from '@/lib/api';
import type { InboxItem, Operation } from '@/app/types';

export const INBOX_STATUS_FILTERS = [
  '',
  'needs_confirmation',
  'failed',
  'completed',
  'undone',
] as const;
export type InboxStatusFilter = (typeof INBOX_STATUS_FILTERS)[number];
export const INBOX_PAGE_SIZE = 30;

export interface InboxPage {
  items: InboxItem[];
  limit: number;
  offset: number;
  has_more: boolean;
}

export function inboxListKey(status: InboxStatusFilter): string[] {
  return ['inbox', status];
}

export function inboxPath(status: InboxStatusFilter): string {
  const query = new URLSearchParams({ limit: String(INBOX_PAGE_SIZE) });
  if (status) query.set('status', status);
  return `/inbox?${query.toString()}`;
}

export function listInbox(status: InboxStatusFilter): Promise<InboxPage> {
  return api.get<InboxPage>(inboxPath(status));
}

export function loadOperation(id: string): Promise<Operation> {
  return api.get<Operation>(`/operations/${id}`);
}

export function retryCapture(id: string): Promise<unknown> {
  return api.post(`/inbox/${id}/retry`);
}

export function undoCapture(id: string): Promise<unknown> {
  return api.post(`/inbox/${id}/undo`);
}

export function rateCapture(id: string, rating: 1 | -1): Promise<unknown> {
  return api.post(`/inbox/${id}/feedback`, { rating });
}

/** The text a capture can be turned into a record with. */
export function captureText(item: InboxItem): string {
  return (item.raw_text ?? item.transcript ?? '').trim();
}

export function shortTitle(text: string, limit = 200): string {
  const single = text.replace(/\s+/g, ' ').trim();
  return single.length <= limit ? single : `${single.slice(0, limit - 1)}\u2026`;
}
