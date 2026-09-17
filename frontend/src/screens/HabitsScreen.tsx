import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { EmptyCard, ErrorCard, ScreenHeader } from '@/components/ScreenHeader';
import { habitLabel } from '@/i18n/habits';
import {
  MEASUREMENT_TYPES,
  WEEKDAYS,
  type HabitChanges,
  type HabitDraft,
  type HabitPage,
  type HabitRecord,
  type MeasurementType,
  checkInValue,
  createHabit,
  deleteHabit,
  disableHabit,
  habitListKey,
  habitProgressKey,
  listHabits,
  loadProgress,
  logHabit,
  patchHabit,
  toggleDay,
} from '@/lib/habits';
import { optionalNumber } from '@/lib/meals';

function draftRecord(draft: HabitDraft): HabitRecord {
  return {
    id: `optimistic-${Date.now()}`,
    name: draft.name,
    measurement_type: draft.measurement_type,
    target_value: draft.target_value ?? null,
    unit: draft.unit ?? null,
    active: true,
    reminder_hour: draft.reminder_hour ?? null,
    source_inbox_item_id: null,
    created_at: new Date().toISOString(),
  };
}

export function HabitsScreen(): JSX.Element {
  const client = useQueryClient();
  const [includeInactive, setIncludeInactive] = useState(false);
  const [name, setName] = useState('');
  const [measurement, setMeasurement] = useState<MeasurementType>('boolean');
  const [target, setTarget] = useState('');
  const [unit, setUnit] = useState('');
  const [hour, setHour] = useState('');
  const [days, setDays] = useState<number[]>([]);
  const [editing, setEditing] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [progressFor, setProgressFor] = useState<string | null>(null);

  const key = habitListKey(includeInactive);
  const query = useQuery({ queryKey: key, queryFn: () => listHabits(includeInactive) });
  const progress = useQuery({
    queryKey: habitProgressKey(progressFor ?? 'none'),
    queryFn: () => loadProgress(progressFor ?? ''),
    enabled: progressFor !== null,
  });
  const t = (label: string): string => habitLabel(null, label);

  const applyOptimistic = async (
    update: (page: HabitPage) => HabitPage,
  ): Promise<{ previous: HabitPage | undefined }> => {
    await client.cancelQueries({ queryKey: key });
    const previous = client.getQueryData<HabitPage>(key);
    if (previous) client.setQueryData<HabitPage>(key, update(previous));
    return { previous };
  };

  const rollback = (context: { previous: HabitPage | undefined } | undefined): void => {
    if (context?.previous) client.setQueryData<HabitPage>(key, context.previous);
  };

  const settle = (): void => void client.invalidateQueries({ queryKey: ['habits'] });

  const create = useMutation({
    mutationFn: (draft: HabitDraft) => createHabit(draft),
    onMutate: (draft: HabitDraft) =>
      applyOptimistic((page) => ({ ...page, items: [...page.items, draftRecord(draft)] })),
    onError: (_error, _draft, context) => rollback(context),
    onSettled: settle,
  });

  const rename = useMutation({
    mutationFn: ({ id, changes }: { id: string; changes: HabitChanges }) =>
      patchHabit(id, changes),
    onMutate: ({ id, changes }: { id: string; changes: HabitChanges }) =>
      applyOptimistic((page) => ({
        ...page,
        items: page.items.map((item) => (item.id === id ? { ...item, ...changes } : item)),
      })),
    onError: (_error, _variables, context) => rollback(context),
    onSettled: settle,
  });

  const stop = useMutation({
    mutationFn: (id: string) => disableHabit(id),
    onMutate: (id: string) =>
      applyOptimistic((page) => ({
        ...page,
        items: page.items.map((item) => (item.id === id ? { ...item, active: false } : item)),
      })),
    onError: (_error, _id, context) => rollback(context),
    onSettled: settle,
  });

  const check = useMutation({
    mutationFn: ({ id, value }: { id: string; value: number }) => logHabit(id, value),
    onSettled: () => {
      void client.invalidateQueries({ queryKey: ['habits'] });
      void client.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => deleteHabit(id),
    onMutate: (id: string) =>
      applyOptimistic((page) => ({
        ...page,
        items: page.items.filter((item) => item.id !== id),
      })),
    onError: (_error, _id, context) => rollback(context),
    onSettled: settle,
  });

  const failed = create.isError || rename.isError || stop.isError || remove.isError || check.isError;

  const submit = (): void => {
    const trimmed = name.trim();
    if (!trimmed) return;
    create.mutate({
      name: trimmed,
      measurement_type: measurement,
      target_value: optionalNumber(target, 100_000),
      unit: unit.trim() ? unit.trim() : null,
      schedule_days: days,
      reminder_hour: optionalNumber(hour, 23),
    });
    setName('');
    setTarget('');
    setUnit('');
    setHour('');
    setDays([]);
  };

  return (
    <section className="p-4">
      <ScreenHeader title={t('habits')} actionTo="/capture" actionLabel="+" />

      <label className="mb-4 flex min-h-touch items-center justify-between gap-4">
        <span>{t('showInactive')}</span>
        <input
          type="checkbox"
          checked={includeInactive}
          onChange={(event) => setIncludeInactive(event.target.checked)}
        />
      </label>

      <form
        className="od-card space-y-3"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <p className="od-label">{t('newHabit')}</p>
        <input
          className="w-full rounded-card border border-line bg-surface p-3"
          aria-label={t('habitName')}
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <label className="block">
          <span className="od-label">{t('measurement')}</span>
          <select
            className="mt-1 w-full rounded-card border border-line bg-surface p-3"
            value={measurement}
            onChange={(event) => setMeasurement(event.target.value as MeasurementType)}
          >
            {MEASUREMENT_TYPES.map((code) => (
              <option key={code} value={code}>
                {t(`measurement_${code}`)}
              </option>
            ))}
          </select>
        </label>
        <div className="grid grid-cols-2 gap-3">
          <input
            className="rounded-card border border-line bg-surface p-3"
            aria-label={t('target')}
            inputMode="numeric"
            value={target}
            onChange={(event) => setTarget(event.target.value)}
          />
          <input
            className="rounded-card border border-line bg-surface p-3"
            aria-label={t('unit')}
            value={unit}
            onChange={(event) => setUnit(event.target.value)}
          />
        </div>
        <input
          className="w-full rounded-card border border-line bg-surface p-3"
          aria-label={t('reminderHour')}
          inputMode="numeric"
          value={hour}
          onChange={(event) => setHour(event.target.value)}
        />
        <fieldset>
          <legend className="od-label">{t('schedule')}</legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {WEEKDAYS.map((day) => (
              <label className="flex items-center gap-1 text-sm" key={day}>
                <input
                  type="checkbox"
                  checked={days.includes(day)}
                  onChange={() => setDays(toggleDay(days, day))}
                />
                <span>{t(`day_${day}`)}</span>
              </label>
            ))}
          </div>
        </fieldset>
        <button className="od-button-primary w-full disabled:opacity-50" disabled={!name.trim()}>
          {t('add')}
        </button>
      </form>

      {failed && (
        <p className="mt-3 rounded-card bg-danger/15 p-3 text-sm text-danger" role="alert">
          {t('saveFailed')}
        </p>
      )}
      {check.isSuccess && (
        <p className="mt-3 rounded-card bg-positive/15 p-3 text-sm text-positive" role="status">
          {t('checkedIn')}
        </p>
      )}
      {progress.data && (
        <div className="od-card mt-3">
          <p className="font-medium">{progress.data.name}</p>
          {progress.data.percent === null ? (
            <p className="mt-1 text-sm text-ink-muted">{t('noProgress')}</p>
          ) : (
            <p className="mt-1 text-sm">
              {progress.data.percent}% {t('progressOf')} ({progress.data.completed}/
              {progress.data.expected})
            </p>
          )}
        </div>
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
                      value={editName}
                      onChange={(event) => setEditName(event.target.value)}
                    />
                    <div className="flex gap-2">
                      <button
                        className="od-button-primary flex-1"
                        onClick={() => {
                          const value = editName.trim();
                          if (value && value !== item.name)
                            rename.mutate({ id: item.id, changes: { name: value } });
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
                    <p className={`font-medium ${item.active ? '' : 'line-through'}`}>
                      {item.name}
                    </p>
                    <p className="mt-1 text-xs text-ink-muted">
                      {t(`measurement_${item.measurement_type}`)}
                      {item.target_value !== null
                        ? ` · ${item.target_value}${item.unit ? ` ${item.unit}` : ''}`
                        : ''}
                      {item.reminder_hour !== null ? ` · ${item.reminder_hour}:00` : ''}
                      {item.active ? '' : ` · ${t('disabled')}`}
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {item.active && (
                        <button
                          className="od-button-ghost text-sm"
                          onClick={() =>
                            check.mutate({ id: item.id, value: checkInValue(item) })
                          }
                        >
                          {t('checkIn')}
                        </button>
                      )}
                      <button
                        className="od-button-ghost text-sm"
                        onClick={() => setProgressFor(item.id)}
                      >
                        {t('progress')}
                      </button>
                      <button
                        className="od-button-ghost text-sm"
                        onClick={() => {
                          setEditing(item.id);
                          setEditName(item.name);
                        }}
                      >
                        {t('edit')}
                      </button>
                      {item.active && (
                        <button
                          className="od-button-ghost text-sm"
                          onClick={() => stop.mutate(item.id)}
                        >
                          {t('disable')}
                        </button>
                      )}
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
