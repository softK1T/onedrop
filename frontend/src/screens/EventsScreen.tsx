import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { EmptyCard, ErrorCard, ScreenHeader } from '@/components/ScreenHeader';
import { eventLabel } from '@/i18n/events';
import {
  EVENT_PERIODS,
  type EventChanges,
  type EventDraft,
  type EventPage,
  type EventPeriod,
  type EventRecord,
  createEvent,
  deleteEvent,
  eventListKey,
  listEvents,
  patchEvent,
} from '@/lib/events';
import { formatDateTime } from '@/lib/format';
import { localDateTimeToIso } from '@/lib/tasks';

function draftRecord(draft: EventDraft): EventRecord {
  return {
    id: `optimistic-${Date.now()}`,
    title: draft.title,
    starts_at: draft.starts_at,
    ends_at: draft.ends_at ?? null,
    location: draft.location ?? null,
    description: draft.description ?? null,
    reminder_at: draft.reminder_at ?? null,
    status: 'planned',
    source_inbox_item_id: null,
    created_at: new Date().toISOString(),
  };
}

export function EventsScreen(): JSX.Element {
  const client = useQueryClient();
  const [period, setPeriod] = useState<EventPeriod>('day');
  const [anchor, setAnchor] = useState('');
  const [title, setTitle] = useState('');
  const [starts, setStarts] = useState('');
  const [ends, setEnds] = useState('');
  const [location, setLocation] = useState('');
  const [editing, setEditing] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  const key = eventListKey(period, anchor);
  const query = useQuery({ queryKey: key, queryFn: () => listEvents(period, anchor) });
  const t = (label: string): string => eventLabel(null, label);

  const applyOptimistic = async (
    update: (page: EventPage) => EventPage,
  ): Promise<{ previous: EventPage | undefined }> => {
    await client.cancelQueries({ queryKey: key });
    const previous = client.getQueryData<EventPage>(key);
    if (previous) client.setQueryData<EventPage>(key, update(previous));
    return { previous };
  };

  const rollback = (context: { previous: EventPage | undefined } | undefined): void => {
    if (context?.previous) client.setQueryData<EventPage>(key, context.previous);
  };

  const settle = (): void => void client.invalidateQueries({ queryKey: ['events'] });

  const create = useMutation({
    mutationFn: (draft: EventDraft) => createEvent(draft),
    onMutate: (draft: EventDraft) =>
      applyOptimistic((page) => ({ ...page, items: [...page.items, draftRecord(draft)] })),
    onError: (_error, _draft, context) => rollback(context),
    onSettled: settle,
  });

  const update = useMutation({
    mutationFn: ({ id, changes }: { id: string; changes: EventChanges }) =>
      patchEvent(id, changes),
    onMutate: ({ id, changes }: { id: string; changes: EventChanges }) =>
      applyOptimistic((page) => ({
        ...page,
        items: page.items.map((item) => (item.id === id ? { ...item, ...changes } : item)),
      })),
    onError: (_error, _variables, context) => rollback(context),
    onSettled: settle,
  });

  const remove = useMutation({
    mutationFn: (id: string) => deleteEvent(id),
    onMutate: (id: string) =>
      applyOptimistic((page) => ({
        ...page,
        items: page.items.filter((item) => item.id !== id),
      })),
    onError: (_error, _id, context) => rollback(context),
    onSettled: settle,
  });

  const failed = create.isError || update.isError || remove.isError;
  const conflicts =
    (create.data?.conflicts.length ?? 0) > 0 || (update.data?.conflicts.length ?? 0) > 0;

  const submit = (): void => {
    const trimmed = title.trim();
    const startsIso = localDateTimeToIso(starts);
    if (!trimmed || !startsIso) return;
    create.mutate({
      title: trimmed,
      starts_at: startsIso,
      ends_at: localDateTimeToIso(ends),
      location: location.trim() ? location.trim() : null,
    });
    setTitle('');
    setStarts('');
    setEnds('');
    setLocation('');
  };

  return (
    <section className="p-4">
      <ScreenHeader title={t('events')} actionTo="/capture" actionLabel="+" />

      <div className="mb-3 flex gap-2" role="tablist">
        {EVENT_PERIODS.map((name) => (
          <button
            key={name}
            role="tab"
            aria-selected={period === name}
            className={`od-button-ghost text-sm ${
              period === name ? 'border-accent text-accent' : ''
            }`}
            onClick={() => setPeriod(name)}
          >
            {t(name)}
          </button>
        ))}
      </div>

      <label className="mb-4 block">
        <span className="od-label">{t('date')}</span>
        <input
          className="mt-1 w-full rounded-card border border-line bg-surface p-3"
          type="date"
          value={anchor}
          onChange={(event) => setAnchor(event.target.value)}
        />
      </label>

      <form
        className="od-card space-y-3"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <p className="od-label">{t('newEvent')}</p>
        <input
          className="w-full rounded-card border border-line bg-surface p-3"
          aria-label={t('eventTitle')}
          value={title}
          onChange={(event) => setTitle(event.target.value)}
        />
        <label className="block">
          <span className="od-label">{t('starts')}</span>
          <input
            className="mt-1 w-full rounded-card border border-line bg-surface p-3"
            type="datetime-local"
            value={starts}
            onChange={(event) => setStarts(event.target.value)}
          />
        </label>
        <label className="block">
          <span className="od-label">{t('ends')}</span>
          <input
            className="mt-1 w-full rounded-card border border-line bg-surface p-3"
            type="datetime-local"
            value={ends}
            onChange={(event) => setEnds(event.target.value)}
          />
        </label>
        <input
          className="w-full rounded-card border border-line bg-surface p-3"
          aria-label={t('location')}
          value={location}
          onChange={(event) => setLocation(event.target.value)}
        />
        <button
          className="od-button-primary w-full disabled:opacity-50"
          disabled={!title.trim() || !starts}
        >
          {t('add')}
        </button>
      </form>

      {failed && (
        <p className="mt-3 rounded-card bg-danger/15 p-3 text-sm text-danger" role="alert">
          {t('saveFailed')}
        </p>
      )}
      {conflicts && (
        <p className="mt-3 rounded-card bg-warning/15 p-3 text-sm text-warning" role="status">
          {t('conflict')}
        </p>
      )}

      <div className="mt-4">
        {query.isLoading && <div className="od-skeleton h-20" aria-busy="true" />}
        {query.isError && (
          <ErrorCard message={t('loadFailed')} retry={() => void query.refetch()} />
        )}
        {query.data && query.data.items.length === 0 && <EmptyCard>{t('empty')}</EmptyCard>}
        {query.data && query.data.items.length > 0 && (
          <ul className="space-y-3">
            {query.data.items.map((item) => (
              <li className="od-card" key={item.id}>
                {editing === item.id ? (
                  <div className="space-y-3">
                    <input
                      className="w-full rounded-card border border-line bg-surface p-3"
                      aria-label={t('edit')}
                      value={editTitle}
                      onChange={(event) => setEditTitle(event.target.value)}
                    />
                    <div className="flex gap-2">
                      <button
                        className="od-button-primary flex-1"
                        onClick={() => {
                          const value = editTitle.trim();
                          if (value && value !== item.title)
                            update.mutate({ id: item.id, changes: { title: value } });
                          setEditing(null);
                        }}
                      >
                        {t('save')}
                      </button>
                      <button className="od-button-ghost flex-1" onClick={() => setEditing(null)}>
                        {t('cancel')}
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <p
                      className={`font-medium ${
                        item.status === 'cancelled' ? 'line-through' : ''
                      }`}
                    >
                      {item.title}
                    </p>
                    <p className="mt-1 text-xs text-ink-muted">
                      {formatDateTime(item.starts_at)}
                      {item.location ? ` · ${item.location}` : ''}
                      {item.status !== 'planned' ? ` · ${t(`status${item.status === 'done' ? 'Done' : 'Cancelled'}`)}` : ''}
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {item.status === 'planned' && (
                        <button
                          className="od-button-ghost text-sm"
                          onClick={() =>
                            update.mutate({ id: item.id, changes: { status: 'done' } })
                          }
                        >
                          {t('complete')}
                        </button>
                      )}
                      {item.status === 'planned' && (
                        <button
                          className="od-button-ghost text-sm"
                          onClick={() =>
                            update.mutate({ id: item.id, changes: { status: 'cancelled' } })
                          }
                        >
                          {t('cancelEvent')}
                        </button>
                      )}
                      <button
                        className="od-button-ghost text-sm"
                        onClick={() => {
                          setEditing(item.id);
                          setEditTitle(item.title);
                        }}
                      >
                        {t('edit')}
                      </button>
                      <button
                        className="od-button-ghost text-sm text-danger"
                        onClick={() => remove.mutate(item.id)}
                      >
                        {t('remove')}
                      </button>
                    </div>
                  </>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
