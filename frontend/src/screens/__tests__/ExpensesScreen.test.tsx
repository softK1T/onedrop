import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import type { Mock } from 'vitest';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { EXPENSE_MESSAGES, expenseLabel } from '@/i18n/expenses';
import { api } from '@/lib/api';
import {
  type ExpensePage,
  type ExpenseRecord,
  type MonthlySummary,
  fromMinorUnits,
  toMinorUnits,
} from '@/lib/expenses';
import { ExpensesScreen } from '@/screens/ExpensesScreen';

vi.mock('@/lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn(), upload: vi.fn() },
  ApiError: class ApiError extends Error {},
}));

const getMock = api.get as unknown as Mock;
const postMock = api.post as unknown as Mock;
const patchMock = api.patch as unknown as Mock;
const delMock = api.del as unknown as Mock;

function expense(overrides: Partial<ExpenseRecord> = {}): ExpenseRecord {
  return {
    id: 'x-1',
    amount_minor: 4500,
    currency: 'PLN',
    base_amount_minor: 4500,
    base_currency: 'PLN',
    fx_rate: '1.00000000',
    category: 'transport',
    merchant: 'Uber',
    occurred_at: '2026-09-17T18:00:00Z',
    description: null,
    source_inbox_item_id: null,
    created_at: '2026-09-17T18:00:00Z',
    ...overrides,
  };
}

function page(items: ExpenseRecord[] = [expense()]): ExpensePage {
  return { items, year: 2026, month: 9, limit: 50, offset: 0, has_more: false };
}

function summary(overrides: Partial<MonthlySummary> = {}): MonthlySummary {
  return {
    year: 2026,
    month: 9,
    base_currency: 'PLN',
    total_minor: 120000,
    previous_total_minor: 100000,
    delta_percent: 20,
    categories: [{ category: 'transport', total_minor: 4500, share_percent: 4 }],
    budget: {
      currency: 'PLN',
      spent_minor: 120000,
      budget_minor: 150000,
      remaining_minor: 30000,
      usage_percent: 80,
      warning: true,
      exceeded: false,
    },
    ...overrides,
  };
}

function route(path: string): unknown {
  return path.startsWith('/expenses/summary') ? summary() : page();
}

function renderExpenses(): HTMLElement {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const { container } = render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ExpensesScreen />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return container;
}

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
  patchMock.mockReset();
  delMock.mockReset();
  getMock.mockImplementation((path: string) => Promise.resolve(route(path)));
  postMock.mockResolvedValue(expense({ id: 'x-2' }));
  patchMock.mockResolvedValue(expense());
  delMock.mockResolvedValue(undefined);
});

describe('ExpensesScreen', () => {
  it('loads the current month list and summary', async () => {
    renderExpenses();

    expect(await screen.findByText('Uber', { exact: false })).toBeInTheDocument();
    const paths = getMock.mock.calls.map((call) => String(call[0]));
    expect(paths.some((path) => path.startsWith('/expenses?year='))).toBe(true);
    expect(paths.some((path) => path.startsWith('/expenses/summary?year='))).toBe(true);
  });

  it('shows the month total, the delta and the category share', async () => {
    const container = renderExpenses();
    await screen.findByText('Spent this month');

    expect(container.textContent).toContain('20%');
    expect(container.textContent).toContain('more than last month');
    expect(container.textContent).toContain('80%');
    expect(screen.getAllByText('Transport').length).toBeGreaterThan(0);
  });

  it('warns when the budget threshold is crossed', async () => {
    renderExpenses();

    expect(await screen.findByRole('status')).toHaveTextContent(
      'You are close to your monthly budget.',
    );
  });

  it('reports an exceeded budget instead of a warning', async () => {
    getMock.mockImplementation((path: string) =>
      Promise.resolve(
        path.startsWith('/expenses/summary')
          ? summary({
              budget: {
                currency: 'PLN',
                spent_minor: 160000,
                budget_minor: 150000,
                remaining_minor: -10000,
                usage_percent: 106,
                warning: true,
                exceeded: true,
              },
            })
          : page(),
      ),
    );

    renderExpenses();

    expect(await screen.findByRole('status')).toHaveTextContent(
      'The monthly budget is exceeded.',
    );
  });

  it('explains a missing budget', async () => {
    getMock.mockImplementation((path: string) =>
      Promise.resolve(
        path.startsWith('/expenses/summary')
          ? summary({
              budget: {
                currency: 'PLN',
                spent_minor: 120000,
                budget_minor: null,
                remaining_minor: null,
                usage_percent: null,
                warning: false,
                exceeded: false,
              },
            })
          : page(),
      ),
    );

    renderExpenses();

    expect(await screen.findByText('No monthly budget set.')).toBeInTheDocument();
  });

  it('asks for another month when the selection changes', async () => {
    renderExpenses();
    await screen.findByText('Spent this month');

    const month = screen.getByLabelText('Month');
    await userEvent.clear(month);
    await userEvent.type(month, '8');

    await waitFor(() =>
      expect(
        getMock.mock.calls.some((call) => String(call[0]).includes('month=8')),
      ).toBe(true),
    );
  });

  it('keeps the add button disabled without an amount', async () => {
    renderExpenses();
    await screen.findByText('Spent this month');

    expect(screen.getByRole('button', { name: 'Add expense' })).toBeDisabled();
  });

  it('creates an expense in integer minor units', async () => {
    postMock.mockReturnValue(new Promise(() => undefined));

    renderExpenses();
    await screen.findByText('Spent this month');
    await userEvent.type(screen.getByLabelText('Amount'), '45');
    await userEvent.selectOptions(screen.getByLabelText('Category'), 'transport');
    await userEvent.type(screen.getByLabelText('Merchant'), 'Bolt');
    await userEvent.click(screen.getByRole('button', { name: 'Add expense' }));

    await waitFor(() =>
      expect(postMock).toHaveBeenCalledWith('/expenses', {
        amount_minor: 4500,
        currency: 'PLN',
        category: 'transport',
        merchant: 'Bolt',
      }),
    );
  });

  it('edits the amount inline', async () => {
    renderExpenses();
    await screen.findByText('Spent this month');
    await userEvent.click(screen.getByRole('button', { name: 'Edit amount' }));

    const field = screen.getByLabelText('Edit amount');
    await userEvent.clear(field);
    await userEvent.type(field, '52.30');
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() =>
      expect(patchMock).toHaveBeenCalledWith('/expenses/x-1', { amount_minor: 5230 }),
    );
  });

  it('deletes an expense optimistically', async () => {
    delMock.mockReturnValue(new Promise(() => undefined));

    renderExpenses();
    await screen.findByText('Spent this month');
    await userEvent.click(screen.getByRole('button', { name: 'Delete' }));

    await waitFor(() => expect(screen.queryByText('Uber', { exact: false })).toBeNull());
    expect(delMock).toHaveBeenCalledWith('/expenses/x-1');
  });

  it('restores a deleted expense when the request fails', async () => {
    delMock.mockRejectedValue(new Error('network down'));

    renderExpenses();
    await screen.findByText('Spent this month');
    await userEvent.click(screen.getByRole('button', { name: 'Delete' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'That change was not saved and has been reverted.',
    );
  });

  it('offers a retry when the list cannot be loaded', async () => {
    getMock.mockImplementation((path: string) =>
      path.startsWith('/expenses/summary')
        ? Promise.resolve(summary())
        : Promise.reject(new Error('network down')),
    );

    renderExpenses();

    expect(await screen.findByText('Could not load expenses.')).toBeInTheDocument();
  });

  it('converts money without floating point drift', () => {
    expect(toMinorUnits('45')).toBe(4500);
    expect(toMinorUnits('45.30')).toBe(4530);
    expect(toMinorUnits('45,30')).toBe(4530);
    expect(toMinorUnits('0.07')).toBe(7);
    expect(toMinorUnits('-5')).toBeNull();
    expect(toMinorUnits('abc')).toBeNull();
    expect(fromMinorUnits(4530)).toBe('45.30');
  });

  it('ships every expense label in every locale', () => {
    const keys = Object.keys(EXPENSE_MESSAGES.en).sort();
    for (const locale of ['en', 'ru', 'pl', 'uk'] as const) {
      expect(Object.keys(EXPENSE_MESSAGES[locale]).sort()).toEqual(keys);
      for (const key of keys) expect(expenseLabel(locale, key)).not.toBe(key);
    }
  });
});
