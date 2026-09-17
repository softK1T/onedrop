import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { EmptyCard, ErrorCard, ScreenHeader } from '@/components/ScreenHeader';
import { mealLabel } from '@/i18n/meals';
import { formatTime } from '@/lib/format';
import {
  MEAL_TYPES,
  type MealChanges,
  type MealDraft,
  type MealPage,
  type MealRecord,
  type MealType,
  createMeal,
  deleteMeal,
  listMeals,
  loadDaily,
  mealDailyKey,
  mealListKey,
  optionalNumber,
  patchMeal,
} from '@/lib/meals';

function draftRecord(draft: MealDraft): MealRecord {
  const now = new Date().toISOString();
  return {
    id: `optimistic-${Date.now()}`,
    title: draft.title,
    meal_type: draft.meal_type,
    eaten_at: now,
    calories: draft.calories ?? null,
    protein: draft.protein ?? null,
    fat: draft.fat ?? null,
    carbohydrates: draft.carbohydrates ?? null,
    estimated: draft.estimated ?? true,
    source_inbox_item_id: null,
    created_at: now,
  };
}

export function MealsScreen(): JSX.Element {
  const client = useQueryClient();
  const [day, setDay] = useState('');
  const [title, setTitle] = useState('');
  const [mealType, setMealType] = useState<MealType>('snack');
  const [calories, setCalories] = useState('');
  const [protein, setProtein] = useState('');
  const [fat, setFat] = useState('');
  const [carbs, setCarbs] = useState('');
  const [editing, setEditing] = useState<string | null>(null);
  const [editCalories, setEditCalories] = useState('');

  const key = mealListKey(day);
  const query = useQuery({ queryKey: key, queryFn: () => listMeals(day) });
  const daily = useQuery({ queryKey: mealDailyKey(day), queryFn: () => loadDaily(day) });
  const t = (label: string): string => mealLabel(null, label);

  const applyOptimistic = async (
    update: (page: MealPage) => MealPage,
  ): Promise<{ previous: MealPage | undefined }> => {
    await client.cancelQueries({ queryKey: key });
    const previous = client.getQueryData<MealPage>(key);
    if (previous) client.setQueryData<MealPage>(key, update(previous));
    return { previous };
  };

  const rollback = (context: { previous: MealPage | undefined } | undefined): void => {
    if (context?.previous) client.setQueryData<MealPage>(key, context.previous);
  };

  const settle = (): void => void client.invalidateQueries({ queryKey: ['meals'] });

  const create = useMutation({
    mutationFn: (draft: MealDraft) => createMeal(draft),
    onMutate: (draft: MealDraft) =>
      applyOptimistic((page) => ({ ...page, items: [...page.items, draftRecord(draft)] })),
    onError: (_error, _draft, context) => rollback(context),
    onSettled: settle,
  });

  const update = useMutation({
    mutationFn: ({ id, changes }: { id: string; changes: MealChanges }) => patchMeal(id, changes),
    onMutate: ({ id, changes }: { id: string; changes: MealChanges }) =>
      applyOptimistic((page) => ({
        ...page,
        items: page.items.map((item) =>
          item.id === id ? { ...item, ...changes, estimated: false } : item,
        ),
      })),
    onError: (_error, _variables, context) => rollback(context),
    onSettled: settle,
  });

  const remove = useMutation({
    mutationFn: (id: string) => deleteMeal(id),
    onMutate: (id: string) =>
      applyOptimistic((page) => ({
        ...page,
        items: page.items.filter((item) => item.id !== id),
      })),
    onError: (_error, _id, context) => rollback(context),
    onSettled: settle,
  });

  const failed = create.isError || update.isError || remove.isError;

  const submit = (): void => {
    const trimmed = title.trim();
    if (!trimmed) return;
    create.mutate({
      title: trimmed,
      meal_type: mealType,
      calories: optionalNumber(calories, 20_000),
      protein: optionalNumber(protein, 2_000),
      fat: optionalNumber(fat, 2_000),
      carbohydrates: optionalNumber(carbs, 2_000),
      estimated: true,
    });
    setTitle('');
    setCalories('');
    setProtein('');
    setFat('');
    setCarbs('');
  };

  return (
    <section className="p-4">
      <ScreenHeader title={t('meals')} actionTo="/capture" actionLabel="+" />

      <label className="mb-4 block">
        <span className="od-label">{t('day')}</span>
        <input
          className="mt-1 w-full rounded-card border border-line bg-surface p-3"
          type="date"
          value={day}
          onChange={(event) => setDay(event.target.value)}
        />
      </label>

      {daily.data && (
        <div className="od-card">
          <p className="text-xs text-ink-muted">{t('dailyTotals')}</p>
          <p className="mt-1 text-2xl font-semibold">
            {daily.data.calories} {t('calories').toLowerCase()}
          </p>
          <p className="mt-1 text-sm text-ink-muted">
            {daily.data.meals_count} {t('mealsCount')} · {t('protein')} {daily.data.protein} ·{' '}
            {t('fat')} {daily.data.fat} · {t('carbs')} {daily.data.carbohydrates}
          </p>
          {daily.data.contains_estimates && (
            <p className="mt-2 rounded-card bg-warning/15 p-2 text-xs text-warning">
              {daily.data.disclaimer}
            </p>
          )}
        </div>
      )}

      <form
        className="od-card mt-4 space-y-3"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <p className="od-label">{t('newMeal')}</p>
        <input
          className="w-full rounded-card border border-line bg-surface p-3"
          aria-label={t('mealTitle')}
          value={title}
          onChange={(event) => setTitle(event.target.value)}
        />
        <label className="block">
          <span className="od-label">{t('mealType')}</span>
          <select
            className="mt-1 w-full rounded-card border border-line bg-surface p-3"
            value={mealType}
            onChange={(event) => setMealType(event.target.value as MealType)}
          >
            {MEAL_TYPES.map((code) => (
              <option key={code} value={code}>
                {t(`type_${code}`)}
              </option>
            ))}
          </select>
        </label>
        <div className="grid grid-cols-2 gap-3">
          <input
            className="rounded-card border border-line bg-surface p-3"
            aria-label={t('calories')}
            inputMode="numeric"
            value={calories}
            onChange={(event) => setCalories(event.target.value)}
          />
          <input
            className="rounded-card border border-line bg-surface p-3"
            aria-label={t('protein')}
            inputMode="numeric"
            value={protein}
            onChange={(event) => setProtein(event.target.value)}
          />
          <input
            className="rounded-card border border-line bg-surface p-3"
            aria-label={t('fat')}
            inputMode="numeric"
            value={fat}
            onChange={(event) => setFat(event.target.value)}
          />
          <input
            className="rounded-card border border-line bg-surface p-3"
            aria-label={t('carbs')}
            inputMode="numeric"
            value={carbs}
            onChange={(event) => setCarbs(event.target.value)}
          />
        </div>
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
                      inputMode="numeric"
                      value={editCalories}
                      onChange={(event) => setEditCalories(event.target.value)}
                    />
                    <div className="flex gap-2">
                      <button
                        className="od-button-primary flex-1"
                        onClick={() => {
                          const next = optionalNumber(editCalories, 20_000);
                          if (next !== null && next !== item.calories)
                            update.mutate({ id: item.id, changes: { calories: next } });
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
                    <p className="font-medium">{item.title}</p>
                    <p className="mt-1 text-xs text-ink-muted">
                      {t(`type_${item.meal_type}`)} · {formatTime(item.eaten_at)}
                      {item.calories !== null ? ` · ${item.calories} kcal` : ''}
                      {item.estimated ? ` · ${t('approximate')}` : ''}
                    </p>
                    <div className="mt-3 flex gap-2">
                      <button
                        className="od-button-ghost text-sm"
                        onClick={() => {
                          setEditing(item.id);
                          setEditCalories(item.calories === null ? '' : String(item.calories));
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
