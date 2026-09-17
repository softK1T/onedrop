import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { EmptyCard, ErrorCard, ScreenHeader } from '@/components/ScreenHeader';
import { collectionLabel } from '@/i18n/collections';
import { formatDateTime } from '@/lib/format';
import {
  TASK_FILTERS,
  TASK_PRIORITIES,
  type TaskDraft,
  type TaskFilter,
  type TaskPage,
  type TaskPriority,
  type TaskRecord,
  completeTask,
  createTask,
  deleteTask,
  listTasks,
  localDateTimeToIso,
  patchTask,
  taskListKey,
} from '@/lib/tasks';

const FILTER_LABELS: Record<TaskFilter, string> = {
  today: 'filterToday',
  upcoming: 'filterUpcoming',
  no_date: 'filterNoDate',
  completed: 'filterCompleted',
  all: 'filterAll',
};

const PRIORITY_LABELS: Record<TaskPriority, string> = {
  low: 'priorityLow',
  normal: 'priorityNormal',
  high: 'priorityHigh',
};

function draftRecord(draft: TaskDraft): TaskRecord {
  return {
    id: `optimistic-${Date.now()}`,
    title: draft.title,
    description: draft.description ?? null,
    due_at: draft.due_at ?? null,
    priority: draft.priority ?? 'normal',
    status: 'open',
    category: null,
    reminder_at: draft.reminder_at ?? null,
    completed_at: null,
    source_inbox_item_id: null,
    created_at: new Date().toISOString(),
  };
}

export function TasksScreen(): JSX.Element {
  const client = useQueryClient();
  const [filter, setFilter] = useState<TaskFilter>('today');
  const [title, setTitle] = useState('');
  const [due, setDue] = useState('');
  const [priority, setPriority] = useState<TaskPriority>('normal');
  const [editing, setEditing] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  const key = taskListKey(filter);
  const query = useQuery({ queryKey: key, queryFn: () => listTasks(filter) });
  const t = (label: string): string => collectionLabel(null, label);

  const applyOptimistic = async (
    update: (page: TaskPage) => TaskPage,
  ): Promise<{ previous: TaskPage | undefined }> => {
    await client.cancelQueries({ queryKey: key });
    const previous = client.getQueryData<TaskPage>(key);
    if (previous) client.setQueryData<TaskPage>(key, update(previous));
    return { previous };
  };

  const rollback = (context: { previous: TaskPage | undefined } | undefined): void => {
    if (context?.previous) client.setQueryData<TaskPage>(key, context.previous);
  };

  const settle = (): void => void client.invalidateQueries({ queryKey: ['tasks'] });

  const create = useMutation({
    mutationFn: (draft: TaskDraft) => createTask(draft),
    onMutate: (draft: TaskDraft) =>
      applyOptimistic((page) => ({ ...page, items: [draftRecord(draft), ...page.items] })),
    onError: (_error, _draft, context) => rollback(context),
    onSettled: settle,
  });

  const rename = useMutation({
    mutationFn: ({ id, value }: { id: string; value: string }) => patchTask(id, { title: value }),
    onMutate: ({ id, value }: { id: string; value: string }) =>
      applyOptimistic((page) => ({
        ...page,
        items: page.items.map((item) => (item.id === id ? { ...item, title: value } : item)),
      })),
    onError: (_error, _variables, context) => rollback(context),
    onSettled: settle,
  });

  const finish = useMutation({
    mutationFn: (id: string) => completeTask(id),
    onMutate: (id: string) =>
      applyOptimistic((page) => ({
        ...page,
        items: page.items.map((item) =>
          item.id === id
            ? { ...item, status: 'done', completed_at: new Date().toISOString() }
            : item,
        ),
      })),
    onError: (_error, _id, context) => rollback(context),
    onSettled: settle,
  });

  const remove = useMutation({
    mutationFn: (id: string) => deleteTask(id),
    onMutate: (id: string) =>
      applyOptimistic((page) => ({
        ...page,
        items: page.items.filter((item) => item.id !== id),
      })),
    onError: (_error, _id, context) => rollback(context),
    onSettled: settle,
  });

  const failed = create.isError || rename.isError || finish.isError || remove.isError;

  const submit = (): void => {
    const trimmed = title.trim();
    if (!trimmed) return;
    create.mutate({ title: trimmed, due_at: localDateTimeToIso(due), priority });
    setTitle('');
    setDue('');
    setPriority('normal');
  };

  return (
    <section className="p-4">
      <ScreenHeader title={t('tasks')} actionTo="/capture" actionLabel="+" />

      <div className="mb-4 flex gap-2 overflow-x-auto" role="tablist">
        {TASK_FILTERS.map((name) => (
          <button
            key={name}
            role="tab"
            aria-selected={filter === name}
            className={`od-button-ghost whitespace-nowrap text-sm ${
              filter === name ? 'border-accent text-accent' : ''
            }`}
            onClick={() => setFilter(name)}
          >
            {t(FILTER_LABELS[name])}
          </button>
        ))}
      </div>

      <form
        className="od-card space-y-3"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <p className="od-label">{t('newTask')}</p>
        <input
          className="w-full rounded-card border border-line bg-surface p-3"
          aria-label={t('newTask')}
          placeholder={t('titlePlaceholder')}
          value={title}
          onChange={(event) => setTitle(event.target.value)}
        />
        <label className="block">
          <span className="od-label">{t('due')}</span>
          <input
            className="mt-1 w-full rounded-card border border-line bg-surface p-3"
            type="datetime-local"
            value={due}
            onChange={(event) => setDue(event.target.value)}
          />
        </label>
        <label className="block">
          <span className="od-label">{t('priority')}</span>
          <select
            className="mt-1 w-full rounded-card border border-line bg-surface p-3"
            value={priority}
            onChange={(event) => setPriority(event.target.value as TaskPriority)}
          >
            {TASK_PRIORITIES.map((name) => (
              <option key={name} value={name}>
                {t(PRIORITY_LABELS[name])}
              </option>
            ))}
          </select>
        </label>
        <button className="od-button-primary w-full disabled:opacity-50" disabled={!title.trim()}>
          {t('add')}
        </button>
      </form>

      {failed && (
        <p className="mt-3 rounded-card bg-danger/15 p-3 text-sm text-danger" role="alert">
          {t('saveFailed')}
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
                          if (value && value !== item.title) rename.mutate({ id: item.id, value });
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
                    <p className={`font-medium ${item.status === 'done' ? 'line-through' : ''}`}>
                      {item.title}
                    </p>
                    <p className="mt-1 text-xs text-ink-muted">
                      {t(PRIORITY_LABELS[(item.priority as TaskPriority) ?? 'normal'])}
                      {item.due_at ? ` · ${formatDateTime(item.due_at)}` : ''}
                    </p>
                    <div className="mt-3 flex gap-2">
                      {item.status !== 'done' && (
                        <button
                          className="od-button-ghost text-sm"
                          onClick={() => finish.mutate(item.id)}
                        >
                          {t('complete')}
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
