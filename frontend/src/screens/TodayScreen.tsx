import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import type { Dashboard } from '@/app/types';
import { EmptyCard, ErrorCard, ScreenHeader } from '@/components/ScreenHeader';
import { todayLabel } from '@/i18n/today';
import { api } from '@/lib/api';
import { formatMoney, formatTime } from '@/lib/format';
import { checkInValue, listHabits, logHabit } from '@/lib/habits';
import { completeTask, patchTask } from '@/lib/tasks';

const DASHBOARD_KEY = ['dashboard', 'today'];
const DAY_IN_MS = 24 * 60 * 60 * 1000;

function Metric({ label, value }: { label: string; value: string | number }): JSX.Element {
  return (
    <div className="od-card">
      <p className="text-xs text-ink-muted">{label}</p>
      <p className="mt-1 text-xl font-semibold">{value}</p>
    </div>
  );
}

/** One day later, keeping the original time of day. */
export function nextDay(iso: string): string {
  return new Date(new Date(iso).getTime() + DAY_IN_MS).toISOString();
}

export function TodayScreen(): JSX.Element {
  const client = useQueryClient();
  const [editing, setEditing] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const t = (label: string): string => todayLabel(null, label);

  const query = useQuery({
    queryKey: DASHBOARD_KEY,
    queryFn: () => api.get<Dashboard>('/dashboard/today'),
  });
  const habits = useQuery({ queryKey: ['habits', false], queryFn: () => listHabits(false) });

  const applyOptimistic = async (
    update: (data: Dashboard) => Dashboard,
  ): Promise<{ previous: Dashboard | undefined }> => {
    await client.cancelQueries({ queryKey: DASHBOARD_KEY });
    const previous = client.getQueryData<Dashboard>(DASHBOARD_KEY);
    if (previous) client.setQueryData<Dashboard>(DASHBOARD_KEY, update(previous));
    return { previous };
  };

  const rollback = (context: { previous: Dashboard | undefined } | undefined): void => {
    if (context?.previous) client.setQueryData<Dashboard>(DASHBOARD_KEY, context.previous);
  };

  const settle = (): void => {
    void client.invalidateQueries({ queryKey: ['dashboard'] });
    void client.invalidateQueries({ queryKey: ['tasks'] });
  };

  const finish = useMutation({
    mutationFn: (id: string) => completeTask(id),
    onMutate: (id: string) =>
      applyOptimistic((data) => ({
        ...data,
        task_items: data.task_items.filter((task) => task.id !== id),
        tasks: { ...data.tasks, today: Math.max(data.tasks.today - 1, 0) },
      })),
    onError: (_error, _id, context) => rollback(context),
    onSettled: settle,
  });

  const postpone = useMutation({
    mutationFn: ({ id, dueAt }: { id: string; dueAt: string }) =>
      patchTask(id, { due_at: dueAt }),
    onMutate: ({ id }: { id: string; dueAt: string }) =>
      applyOptimistic((data) => ({
        ...data,
        task_items: data.task_items.filter((task) => task.id !== id),
      })),
    onError: (_error, _variables, context) => rollback(context),
    onSettled: settle,
  });

  const rename = useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) => patchTask(id, { title }),
    onMutate: ({ id, title }: { id: string; title: string }) =>
      applyOptimistic((data) => ({
        ...data,
        task_items: data.task_items.map((task) =>
          task.id === id ? { ...task, title } : task,
        ),
      })),
    onError: (_error, _variables, context) => rollback(context),
    onSettled: settle,
  });

  const check = useMutation({
    mutationFn: ({ id, value }: { id: string; value: number }) => logHabit(id, value),
    onSettled: () => {
      void client.invalidateQueries({ queryKey: ['dashboard'] });
      void client.invalidateQueries({ queryKey: ['habits'] });
    },
  });

  const failed = finish.isError || postpone.isError || rename.isError || check.isError;

  if (query.isLoading) {
    return (
      <section className="p-4" aria-busy="true">
        <div className="od-skeleton h-8 w-28" />
        <div className="mt-5 grid grid-cols-2 gap-3">
          <div className="od-skeleton h-20" />
          <div className="od-skeleton h-20" />
        </div>
      </section>
    );
  }
  if (query.isError || !query.data) {
    return (
      <section className="p-4">
        <ErrorCard message={t('loadFailed')} retry={() => void query.refetch()} />
      </section>
    );
  }

  const data = query.data;

  return (
    <section className="p-4">
      <ScreenHeader title={t('title')} actionTo="/capture" actionLabel="+" />

      {data.budget_warning && (
        <div className="mb-3 rounded-card bg-warning/15 p-3 text-sm text-warning">
          {t('budgetWarning')}
        </div>
      )}
      {failed && (
        <p className="mb-3 rounded-card bg-danger/15 p-3 text-sm text-danger" role="alert">
          {t('saveFailed')}
        </p>
      )}
      {check.isSuccess && (
        <p className="mb-3 rounded-card bg-positive/15 p-3 text-sm text-positive" role="status">
          {t('checkedIn')}
        </p>
      )}

      <div className="grid grid-cols-2 gap-3">
        <Metric label={t('tasks')} value={data.tasks.today} />
        <Metric label={t('aiLeft')} value={data.ai.remaining} />
        <Metric
          label={t('spent')}
          value={formatMoney(data.expenses_today_minor, data.base_currency)}
        />
        <Metric label={t('calories')} value={data.nutrition.calories} />
      </div>

      <div className="mt-6 space-y-3">
        <h2 className="font-semibold">{t('tasks')}</h2>
        {data.task_items.length === 0 && <EmptyCard>{t('empty')}</EmptyCard>}
        {data.task_items.map((task) => (
          <div className="od-card" key={task.id}>
            {editing === task.id ? (
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
                      if (value && value !== task.title)
                        rename.mutate({ id: task.id, title: value });
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
                <p className="font-medium">{task.title}</p>
                <p className="mt-1 text-xs text-ink-muted">
                  {task.priority}
                  {task.due_at ? ` · ${formatTime(task.due_at)}` : ` · ${t('noDue')}`}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    className="od-button-ghost text-sm"
                    onClick={() => finish.mutate(task.id)}
                  >
                    {t('done')}
                  </button>
                  <button
                    className="od-button-ghost text-sm"
                    disabled={task.due_at === null}
                    onClick={() => {
                      if (task.due_at)
                        postpone.mutate({ id: task.id, dueAt: nextDay(task.due_at) });
                    }}
                  >
                    {t('postpone')}
                  </button>
                  <button
                    className="od-button-ghost text-sm"
                    onClick={() => {
                      setEditing(task.id);
                      setEditTitle(task.title);
                    }}
                  >
                    {t('edit')}
                  </button>
                </div>
              </>
            )}
          </div>
        ))}
      </div>

      <div className="mt-6 space-y-3">
        <h2 className="font-semibold">{t('events')}</h2>
        {data.events.length === 0 && <EmptyCard>{t('empty')}</EmptyCard>}
        {data.events.map((event) => (
          <Link to="/events" className="od-card block" key={event.id}>
            <p className="font-medium">{event.title}</p>
            <p className="mt-1 text-xs text-ink-muted">{formatTime(event.starts_at)}</p>
          </Link>
        ))}
      </div>

      <div className="mt-6 space-y-3">
        <h2 className="font-semibold">{t('habits')}</h2>
        {habits.data && habits.data.items.length === 0 && (
          <EmptyCard>{t('noHabits')}</EmptyCard>
        )}
        {habits.data?.items.map((habit) => (
          <div className="od-card flex items-center justify-between gap-3" key={habit.id}>
            <span className="font-medium">{habit.name}</span>
            <button
              className="od-button-ghost text-sm"
              onClick={() => check.mutate({ id: habit.id, value: checkInValue(habit) })}
            >
              {t('checkIn')}
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}
