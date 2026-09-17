import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useParams } from 'react-router-dom';

import type { InboxItem } from '@/app/types';
import { EmptyCard, ErrorCard, ScreenHeader } from '@/components/ScreenHeader';
import { inboxLabel } from '@/i18n/inbox';
import { createEvent } from '@/lib/events';
import { entityLabel, formatDateTime } from '@/lib/format';
import {
  INBOX_STATUS_FILTERS,
  type InboxStatusFilter,
  captureText,
  inboxListKey,
  listInbox,
  loadOperation,
  rateCapture,
  retryCapture,
  shortTitle,
  undoCapture,
} from '@/lib/inbox';
import { createNote } from '@/lib/notes';
import { createTask, localDateTimeToIso } from '@/lib/tasks';

const FILTER_LABELS: Record<InboxStatusFilter, string> = {
  '': 'filterAll',
  needs_confirmation: 'filterNeedsConfirmation',
  failed: 'filterFailed',
  completed: 'filterCompleted',
  undone: 'filterUndone',
};

function Status({ value }: { value: string }): JSX.Element {
  return (
    <span className="rounded-full bg-line px-2 py-1 text-xs text-ink-muted">
      {value.replaceAll('_', ' ')}
    </span>
  );
}

export function InboxScreen(): JSX.Element {
  const { id } = useParams();
  const client = useQueryClient();
  const [status, setStatus] = useState<InboxStatusFilter>('');
  const [eventFor, setEventFor] = useState<string | null>(null);
  const [eventStart, setEventStart] = useState('');
  const t = (label: string): string => inboxLabel(null, label);

  const list = useQuery({ queryKey: inboxListKey(status), queryFn: () => listInbox(status) });
  const operation = useQuery({
    queryKey: ['operation', id ?? 'none'],
    queryFn: () => loadOperation(id ?? ''),
    enabled: Boolean(id),
    refetchInterval: (query) =>
      ['received', 'queued', 'processing'].includes(query.state.data?.status ?? '') ? 1500 : false,
  });

  const invalidate = (): void => {
    void client.invalidateQueries({ queryKey: ['inbox'] });
    void client.invalidateQueries({ queryKey: ['operation'] });
  };

  const retry = useMutation({ mutationFn: retryCapture, onSuccess: invalidate });
  const undo = useMutation({ mutationFn: undoCapture, onSuccess: invalidate });
  const rate = useMutation({
    mutationFn: ({ itemId, rating }: { itemId: string; rating: 1 | -1 }) =>
      rateCapture(itemId, rating),
  });
  const toTask = useMutation({
    mutationFn: (text: string) => createTask({ title: shortTitle(text) }),
    onSuccess: () => void client.invalidateQueries({ queryKey: ['tasks'] }),
  });
  const toNote = useMutation({
    mutationFn: (text: string) => createNote({ content: text }),
    onSuccess: () => void client.invalidateQueries({ queryKey: ['notes'] }),
  });
  const toEvent = useMutation({
    mutationFn: ({ text, startsAt }: { text: string; startsAt: string }) =>
      createEvent({ title: shortTitle(text), starts_at: startsAt }),
    onSuccess: () => void client.invalidateQueries({ queryKey: ['events'] }),
  });

  const actionFailed =
    retry.isError || undo.isError || rate.isError || toTask.isError || toNote.isError ||
    toEvent.isError;

  if (id && operation.data) {
    const data = operation.data;
    return (
      <section className="p-4">
        <ScreenHeader title={t('inbox')} />
        <div className="od-card">
          <div className="flex items-start justify-between gap-3">
            <Status value={data.status} />
            <span className="text-xs text-ink-muted">{data.input_type}</span>
          </div>
          {data.transcript && <p className="mt-3 text-sm">{data.transcript}</p>}
          {data.clarification_question && (
            <p className="mt-3 rounded-card bg-warning/15 p-3 text-sm text-warning">
              {data.clarification_question}
            </p>
          )}
          {data.error && <p className="mt-3 text-sm text-danger">{data.error}</p>}
          <div className="mt-4 space-y-2">
            {data.created.map((entry) => (
              <div
                className="rounded-card border border-line p-3"
                key={`${entry.entity_type}:${entry.entity_id}`}
              >
                {entityLabel(entry.entity_type)}
              </div>
            ))}
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {data.status === 'failed' && (
              <button
                className="od-button-ghost text-sm"
                onClick={() => retry.mutate(data.inbox_item_id)}
              >
                {t('retry')}
              </button>
            )}
            {data.status === 'completed' && (
              <>
                <button
                  className="od-button-ghost text-sm text-danger"
                  onClick={() => undo.mutate(data.inbox_item_id)}
                >
                  {t('undo')}
                </button>
                <button
                  className="od-button-ghost text-sm"
                  onClick={() => rate.mutate({ itemId: data.inbox_item_id, rating: 1 })}
                >
                  {t('helpful')}
                </button>
                <button
                  className="od-button-ghost text-sm"
                  onClick={() => rate.mutate({ itemId: data.inbox_item_id, rating: -1 })}
                >
                  {t('notHelpful')}
                </button>
              </>
            )}
          </div>
          {rate.isSuccess && (
            <p className="mt-3 text-sm text-positive" role="status">
              {t('rated')}
            </p>
          )}
        </div>
      </section>
    );
  }

  return (
    <section className="p-4">
      <ScreenHeader title={t('inbox')} actionTo="/capture" actionLabel="+" />

      <div className="mb-4 flex gap-2 overflow-x-auto" role="tablist">
        {INBOX_STATUS_FILTERS.map((name) => (
          <button
            key={name || 'all'}
            role="tab"
            aria-selected={status === name}
            className={`od-button-ghost whitespace-nowrap text-sm ${
              status === name ? 'border-accent text-accent' : ''
            }`}
            onClick={() => setStatus(name)}
          >
            {t(FILTER_LABELS[name])}
          </button>
        ))}
      </div>

      {actionFailed && (
        <p className="mb-3 rounded-card bg-danger/15 p-3 text-sm text-danger" role="alert">
          {t('actionFailed')}
        </p>
      )}
      {toTask.isSuccess && (
        <p className="mb-3 rounded-card bg-positive/15 p-3 text-sm text-positive" role="status">
          {t('createdTask')}
        </p>
      )}
      {toNote.isSuccess && (
        <p className="mb-3 rounded-card bg-positive/15 p-3 text-sm text-positive" role="status">
          {t('createdNote')}
        </p>
      )}
      {toEvent.isSuccess && (
        <p className="mb-3 rounded-card bg-positive/15 p-3 text-sm text-positive" role="status">
          {t('createdEvent')}
        </p>
      )}
      {rate.isSuccess && (
        <p className="mb-3 rounded-card bg-positive/15 p-3 text-sm text-positive" role="status">
          {t('rated')}
        </p>
      )}

      {list.isLoading && <div className="od-skeleton h-20" aria-busy="true" />}
      {list.isError && <ErrorCard message={t('loadFailed')} retry={() => void list.refetch()} />}
      {list.data && list.data.items.length === 0 && <EmptyCard>{t('empty')}</EmptyCard>}
      {list.data && list.data.items.length > 0 && (
        <ul className="space-y-3">
          {list.data.items.map((item: InboxItem) => {
            const text = captureText(item);
            return (
              <li className="od-card" key={item.id}>
                <div className="flex justify-between gap-3">
                  <a className="line-clamp-2 font-medium" href={`/inbox/${item.id}`}>
                    {text || item.input_type}
                  </a>
                  <Status value={item.status} />
                </div>
                <p className="mt-2 text-xs text-ink-muted">{formatDateTime(item.created_at)}</p>
                {item.error && <p className="mt-2 text-xs text-danger">{item.error}</p>}

                <div className="mt-3 flex flex-wrap gap-2">
                  {item.status === 'failed' && (
                    <button
                      className="od-button-ghost text-sm"
                      onClick={() => retry.mutate(item.id)}
                    >
                      {t('retry')}
                    </button>
                  )}
                  {item.status === 'completed' && (
                    <button
                      className="od-button-ghost text-sm text-danger"
                      onClick={() => undo.mutate(item.id)}
                    >
                      {t('undo')}
                    </button>
                  )}
                  <button
                    className="od-button-ghost text-sm"
                    disabled={!text}
                    onClick={() => toTask.mutate(text)}
                  >
                    {t('makeTask')}
                  </button>
                  <button
                    className="od-button-ghost text-sm"
                    disabled={!text}
                    onClick={() => toNote.mutate(text)}
                  >
                    {t('makeNote')}
                  </button>
                  <button
                    className="od-button-ghost text-sm"
                    disabled={!text}
                    onClick={() => {
                      setEventFor(item.id);
                      setEventStart('');
                    }}
                  >
                    {t('makeEvent')}
                  </button>
                  <button
                    className="od-button-ghost text-sm"
                    onClick={() => rate.mutate({ itemId: item.id, rating: 1 })}
                  >
                    {t('helpful')}
                  </button>
                  <button
                    className="od-button-ghost text-sm"
                    onClick={() => rate.mutate({ itemId: item.id, rating: -1 })}
                  >
                    {t('notHelpful')}
                  </button>
                </div>

                {!text && <p className="mt-2 text-xs text-ink-muted">{t('noText')}</p>}

                {eventFor === item.id && (
                  <div className="mt-3 space-y-2 rounded-card border border-line p-3">
                    <label className="block">
                      <span className="od-label">{t('eventStart')}</span>
                      <input
                        className="mt-1 w-full rounded-card border border-line bg-surface p-3"
                        type="datetime-local"
                        value={eventStart}
                        onChange={(event) => setEventStart(event.target.value)}
                      />
                    </label>
                    <div className="flex gap-2">
                      <button
                        className="od-button-primary flex-1 disabled:opacity-50"
                        disabled={!eventStart}
                        onClick={() => {
                          const startsAt = localDateTimeToIso(eventStart);
                          if (startsAt) toEvent.mutate({ text, startsAt });
                          setEventFor(null);
                        }}
                      >
                        {t('create')}
                      </button>
                      <button
                        className="od-button-ghost flex-1"
                        onClick={() => setEventFor(null)}
                      >
                        {t('cancel')}
                      </button>
                    </div>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
