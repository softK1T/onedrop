import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { EmptyCard, ErrorCard, ScreenHeader } from '@/components/ScreenHeader';
import { expenseLabel } from '@/i18n/expenses';
import {
  EXPENSE_CATEGORIES,
  EXPENSE_CURRENCIES,
  type ExpenseCategory,
  type ExpenseChanges,
  type ExpenseCurrency,
  type ExpenseDraft,
  type ExpensePage,
  type ExpenseRecord,
  createExpense,
  currentMonth,
  deleteExpense,
  expenseListKey,
  expenseSummaryKey,
  fromMinorUnits,
  listExpenses,
  loadSummary,
  patchExpense,
  toMinorUnits,
} from '@/lib/expenses';
import { formatMoney } from '@/lib/format';

function draftRecord(draft: ExpenseDraft): ExpenseRecord {
  const now = new Date().toISOString();
  return {
    id: `optimistic-${Date.now()}`,
    amount_minor: draft.amount_minor,
    currency: draft.currency,
    base_amount_minor: null,
    base_currency: null,
    fx_rate: null,
    category: draft.category,
    merchant: draft.merchant ?? null,
    occurred_at: draft.occurred_at ?? now,
    description: draft.description ?? null,
    source_inbox_item_id: null,
    created_at: now,
  };
}

export function ExpensesScreen(): JSX.Element {
  const client = useQueryClient();
  const [selection, setSelection] = useState(currentMonth());
  const [amount, setAmount] = useState('');
  const [currency, setCurrency] = useState<ExpenseCurrency>('PLN');
  const [category, setCategory] = useState<ExpenseCategory>('other');
  const [merchant, setMerchant] = useState('');
  const [editing, setEditing] = useState<string | null>(null);
  const [editAmount, setEditAmount] = useState('');

  const key = expenseListKey(selection);
  const query = useQuery({ queryKey: key, queryFn: () => listExpenses(selection) });
  const summary = useQuery({
    queryKey: expenseSummaryKey(selection),
    queryFn: () => loadSummary(selection),
  });
  const t = (label: string): string => expenseLabel(null, label);

  const applyOptimistic = async (
    update: (page: ExpensePage) => ExpensePage,
  ): Promise<{ previous: ExpensePage | undefined }> => {
    await client.cancelQueries({ queryKey: key });
    const previous = client.getQueryData<ExpensePage>(key);
    if (previous) client.setQueryData<ExpensePage>(key, update(previous));
    return { previous };
  };

  const rollback = (context: { previous: ExpensePage | undefined } | undefined): void => {
    if (context?.previous) client.setQueryData<ExpensePage>(key, context.previous);
  };

  const settle = (): void => void client.invalidateQueries({ queryKey: ['expenses'] });

  const create = useMutation({
    mutationFn: (draft: ExpenseDraft) => createExpense(draft),
    onMutate: (draft: ExpenseDraft) =>
      applyOptimistic((page) => ({ ...page, items: [draftRecord(draft), ...page.items] })),
    onError: (_error, _draft, context) => rollback(context),
    onSettled: settle,
  });

  const update = useMutation({
    mutationFn: ({ id, changes }: { id: string; changes: ExpenseChanges }) =>
      patchExpense(id, changes),
    onMutate: ({ id, changes }: { id: string; changes: ExpenseChanges }) =>
      applyOptimistic((page) => ({
        ...page,
        items: page.items.map((item) => (item.id === id ? { ...item, ...changes } : item)),
      })),
    onError: (_error, _variables, context) => rollback(context),
    onSettled: settle,
  });

  const remove = useMutation({
    mutationFn: (id: string) => deleteExpense(id),
    onMutate: (id: string) =>
      applyOptimistic((page) => ({
        ...page,
        items: page.items.filter((item) => item.id !== id),
      })),
    onError: (_error, _id, context) => rollback(context),
    onSettled: settle,
  });

  const failed = create.isError || update.isError || remove.isError;
  const minor = toMinorUnits(amount);

  const submit = (): void => {
    if (minor === null || minor === 0) return;
    create.mutate({
      amount_minor: minor,
      currency,
      category,
      merchant: merchant.trim() ? merchant.trim() : null,
    });
    setAmount('');
    setMerchant('');
  };

  return (
    <section className="p-4">
      <ScreenHeader title={t('expenses')} actionTo="/capture" actionLabel="+" />

      <div className="mb-4 grid grid-cols-2 gap-3">
        <label className="block">
          <span className="od-label">{t('year')}</span>
          <input
            className="mt-1 w-full rounded-card border border-line bg-surface p-3"
            type="number"
            min={2000}
            max={2100}
            value={selection.year}
            onChange={(event) =>
              setSelection({ ...selection, year: Number(event.target.value) || selection.year })
            }
          />
        </label>
        <label className="block">
          <span className="od-label">{t('month')}</span>
          <input
            className="mt-1 w-full rounded-card border border-line bg-surface p-3"
            type="number"
            min={1}
            max={12}
            value={selection.month}
            onChange={(event) =>
              setSelection({ ...selection, month: Number(event.target.value) || selection.month })
            }
          />
        </label>
      </div>

      {summary.data && (
        <div className="od-card">
          <p className="text-xs text-ink-muted">{t('total')}</p>
          <p className="mt-1 text-2xl font-semibold">
            {formatMoney(summary.data.total_minor, summary.data.base_currency)}
          </p>
          {summary.data.delta_percent !== null && (
            <p className="mt-1 text-xs text-ink-muted">
              {Math.abs(summary.data.delta_percent)}%{' '}
              {summary.data.delta_percent >= 0 ? t('deltaUp') : t('deltaDown')}
            </p>
          )}
          {summary.data.budget.usage_percent !== null ? (
            <p className="mt-2 text-sm">
              {summary.data.budget.usage_percent}% {t('budgetUsed')}
            </p>
          ) : (
            <p className="mt-2 text-sm text-ink-muted">{t('noBudget')}</p>
          )}
          {summary.data.budget.exceeded && (
            <p className="mt-2 rounded-card bg-danger/15 p-2 text-sm text-danger" role="status">
              {t('budgetExceeded')}
            </p>
          )}
          {!summary.data.budget.exceeded && summary.data.budget.warning && (
            <p className="mt-2 rounded-card bg-warning/15 p-2 text-sm text-warning" role="status">
              {t('budgetWarning')}
            </p>
          )}
          {summary.data.categories.length > 0 && (
            <ul className="mt-3 space-y-1 text-sm">
              {summary.data.categories.map((entry) => (
                <li className="flex justify-between" key={entry.category}>
                  <span>{t(`cat_${entry.category}`)}</span>
                  <span className="text-ink-muted">
                    {formatMoney(entry.total_minor, summary.data.base_currency)} ·{' '}
                    {entry.share_percent}%
                  </span>
                </li>
              ))}
            </ul>
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
        <p className="od-label">{t('newExpense')}</p>
        <input
          className="w-full rounded-card border border-line bg-surface p-3"
          aria-label={t('amount')}
          inputMode="decimal"
          value={amount}
          onChange={(event) => setAmount(event.target.value)}
        />
        <label className="block">
          <span className="od-label">{t('currency')}</span>
          <select
            className="mt-1 w-full rounded-card border border-line bg-surface p-3"
            value={currency}
            onChange={(event) => setCurrency(event.target.value as ExpenseCurrency)}
          >
            {EXPENSE_CURRENCIES.map((code) => (
              <option key={code} value={code}>
                {code}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="od-label">{t('category')}</span>
          <select
            className="mt-1 w-full rounded-card border border-line bg-surface p-3"
            value={category}
            onChange={(event) => setCategory(event.target.value as ExpenseCategory)}
          >
            {EXPENSE_CATEGORIES.map((code) => (
              <option key={code} value={code}>
                {t(`cat_${code}`)}
              </option>
            ))}
          </select>
        </label>
        <input
          className="w-full rounded-card border border-line bg-surface p-3"
          aria-label={t('merchant')}
          value={merchant}
          onChange={(event) => setMerchant(event.target.value)}
        />
        <button
          className="od-button-primary w-full disabled:opacity-50"
          disabled={miner(minor)}
        >
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
                      inputMode="decimal"
                      value={editAmount}
                      onChange={(event) => setEditAmount(event.target.value)}
                    />
                    <div className="flex gap-2">
                      <button
                        className="od-button-primary flex-1"
                        onClick={() => {
                          const next = toMinorUnits(editAmount);
                          if (next !== null && next !== item.amount_minor)
                            update.mutate({ id: item.id, changes: { amount_minor: next } });
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
                    <p className="font-medium">
                      {formatMoney(item.amount_minor, item.currency)}
                    </p>
                    <p className="mt-1 text-xs text-ink-muted">
                      {t(`cat_${item.category}`)}
                      {item.merchant ? ` · ${item.merchant}` : ''}
                      {item.base_amount_minor !== null && item.base_currency
                        ? ` · ${formatMoney(item.base_amount_minor, item.base_currency)} ${t('converted')}`
                        : ''}
                    </p>
                    <div className="mt-3 flex gap-2">
                      <button
                        className="od-button-ghost text-sm"
                        onClick={() => {
                          setEditing(item.id);
                          setEditAmount(fromMinorUnits(item.amount_minor));
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

function miner(minor: number | null): boolean {
  return minor === null || minor === 0;
}
