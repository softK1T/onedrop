import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';

import type { InboxItem, Operation } from '@/app/types';
import { EmptyCard, ErrorCard, ScreenHeader } from '@/components/ScreenHeader';
import { entityLabel, formatDateTime } from '@/lib/format';
import { api } from '@/lib/api';

interface InboxPage { items: InboxItem[]; has_more: boolean }

function Status({ value }: { value: string }): JSX.Element { return <span className="rounded-full bg-line px-2 py-1 text-xs text-ink-muted">{value.replaceAll('_', ' ')}</span>; }

export function InboxScreen(): JSX.Element {
  const { id } = useParams(); const client = useQueryClient();
  const list = useQuery({ queryKey: ['inbox'], queryFn: () => api.get<InboxPage>('/inbox?limit=30') });
  const operation = useQuery({ queryKey: ['operation', id], queryFn: () => api.get<Operation>(`/operations/${id}`), enabled: Boolean(id), refetchInterval: (query) => ['received','queued','processing'].includes(query.state.data?.status ?? '') ? 1500 : false });
  const retry = useMutation({ mutationFn: (itemId: string) => api.post(`/inbox/${itemId}/retry`), onSuccess: () => void client.invalidateQueries({ queryKey: ['inbox'] }) });
  const undo = useMutation({ mutationFn: (itemId: string) => api.post(`/inbox/${itemId}/undo`), onSuccess: () => { void client.invalidateQueries({ queryKey: ['inbox'] }); void client.invalidateQueries({ queryKey: ['operation', id] }); } });
  if (id && operation.data) return <section className="p-4"><ScreenHeader title="Capture" /><div className="od-card"><div className="flex items-start justify-between gap-3"><Status value={operation.data.status} /><span className="text-xs text-ink-muted">{operation.data.input_type}</span></div>{operation.data.transcript && <p className="mt-3 text-sm">{operation.data.transcript}</p>}{operation.data.clarification_question && <p className="mt-3 rounded-card bg-warning/15 p-3 text-sm text-warning">{operation.data.clarification_question}</p>}{operation.data.error && <p className="mt-3 text-sm text-danger">{operation.data.error}</p>}<div className="mt-4 space-y-2">{operation.data.created.map(item => <div className="rounded-card border border-line p-3" key={`${item.entity_type}:${item.entity_id}`}>{entityLabel(item.entity_type)}</div>)}</div>{operation.data.status === 'failed' && <button className="od-button-ghost mt-4" onClick={() => retry.mutate(operation.data.inbox_item_id)}>Retry</button>}{operation.data.status === 'completed' && <button className="od-button-ghost mt-4 text-danger" onClick={() => undo.mutate(operation.data.inbox_item_id)}>Undo all</button>}</div></section>;
  if (list.isLoading) return <section className="p-4"><div className="od-skeleton h-8 w-24" /><div className="od-skeleton mt-5 h-20" /></section>;
  if (list.isError) return <section className="p-4"><ErrorCard message="Could not load captures." retry={() => void list.refetch()} /></section>;
  if (!list.data) return <section className="p-4"><EmptyCard>No captures yet.</EmptyCard></section>;
  return <section className="p-4"><ScreenHeader title="Inbox" />{list.data.items.length ? <div className="space-y-3">{list.data.items.map(item => <a className="od-card block" href={`/inbox/${item.id}`} key={item.id}><div className="flex justify-between gap-3"><p className="line-clamp-2 font-medium">{item.raw_text ?? item.transcript ?? item.input_type}</p><Status value={item.status} /></div><p className="mt-2 text-xs text-ink-muted">{formatDateTime(item.created_at)}</p>{item.status === 'failed' && <button className="od-button-ghost mt-3 text-sm" onClick={(event) => { event.preventDefault(); retry.mutate(item.id); }}>Retry</button>}</a>)}</div> : <EmptyCard>No captures yet.</EmptyCard>}</section>;
}
