import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import type { Mock } from 'vitest';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { Dashboard } from '@/app/types';
import { TODAY_MESSAGES, todayLabel } from '@/i18n/today';
import { api } from '@/lib/api';
import type { HabitPage } from '@/lib/habits';
import { TodayScreen, nextDay } from '@/screens/TodayScreen';

vi.mock('@/lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn(), upload: vi.fn() },
  ApiError: class ApiError extends Error {},
}));

const getMock = api.get as unknown as Mock;
const postMock = api.post as unknown as Mock;
const patchMock = api.patch as unknown as Mock;

function dashboard(overrides: Partial<Dashboard> = {}): Dashboard {
  return {
    day: '2026-09-18',
    timezone: 'Europe/Warsaw',
    tasks: { today: 2, overdue: 1, completed_today: 3, open_total: 5 },
    task_items: [
      {
        id: 't-1',
        title: 'Pay the internet bill',
        due_at: '2026-09-18T15:00:00Z',
        priority: 'high',
        status: 'open',
      },
    ],
    events: [
      { id: 'e-1', title: 'Meeting with Andrew', starts_at: '2026-09-18T13:00:00Z', ends_at: null },
    ],
    expenses_today_minor: 4500,
    base_currency: 'PLN',
    nutrition: {
      calories: 1850,
      protein: 90,
      fat: 60,
      carbohydrates: 200,
      contains_estimates: true,
    },
    budget_warning: false,
    ai: { plan: 'free', remaining: 7 },
    ...overrides,
  };
}

function habitPage(): HabitPage {
  return {
    items: [
      {
        id: 'h-1',
        name: 'Morning workout',
        measurement_type: 'boolean',
        target_value: null,
        unit: null,
        active: true,
        reminder_hour: 7,
        source_inbox_item_id: null,
        created_at: '2026-09-17T10:00:00Z',
      },
    ],
    limit: 50,
    offset: 0,
    has_more: false,
  };
}

function route(path: string): unknown {
  return String(path).startsWith('/habits') ? habitPage() : dashboard();
}

function renderToday(): HTMLElement {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const { container } = render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <TodayScreen />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return container;
}

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
  patchMock.mockReset();
  getMock.mockImplementation((path: string) => Promise.resolve(route(path)));
  postMock.mockResolvedValue({});
  patchMock.mockResolvedValue({});
});

describe('TodayScreen', () => {
  it('renders a busy skeleton while the dashboard loads', () => {
    getMock.mockReturnValue(new Promise(() => undefined));

    const container = renderToday();

    expect(container.querySelector('[aria-busy="true"]')).not.toBeNull();
  });

  it('shows the metrics, tasks, events and habits', async () => {
    renderToday();

    expect(await screen.findByRole('heading', { level: 1, name: 'Today' })).toBeInTheDocument();
    expect(screen.getByText('Pay the internet bill')).toBeInTheDocument();
    expect(screen.getByText('Meeting with Andrew')).toBeInTheDocument();
    expect(await screen.findByText('Morning workout')).toBeInTheDocument();
    expect(screen.getByText('AI actions left')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
  });

  it('completes a task and drops it from the day immediately', async () => {
    postMock.mockReturnValue(new Promise(() => undefined));

    renderToday();
    await screen.findByText('Pay the internet bill');
    await userEvent.click(screen.getByRole('button', { name: 'Done' }));

    await waitFor(() => expect(screen.queryByText('Pay the internet bill')).toBeNull());
    expect(postMock).toHaveBeenCalledWith('/tasks/t-1/complete');
  });

  it('postpones a task by exactly one day', async () => {
    patchMock.mockReturnValue(new Promise(() => undefined));

    renderToday();
    await screen.findByText('Pay the internet bill');
    await userEvent.click(screen.getByRole('button', { name: 'Tomorrow' }));

    await waitFor(() =>
      expect(patchMock).toHaveBeenCalledWith('/tasks/t-1', {
        due_at: '2026-09-19T15:00:00.000Z',
      }),
    );
  });

  it('cannot postpone a task without a due date', async () => {
    getMock.mockImplementation((path: string) =>
      Promise.resolve(
        String(path).startsWith('/habits')
          ? habitPage()
          : dashboard({
              task_items: [
                {
                  id: 't-2',
                  title: 'Someday task',
                  due_at: null,
                  priority: 'low',
                  status: 'open',
                },
              ],
            }),
      ),
    );

    renderToday();
    await screen.findByText('Someday task');

    expect(screen.getByRole('button', { name: 'Tomorrow' })).toBeDisabled();
    expect(screen.getByText(/no date, cannot postpone/)).toBeInTheDocument();
  });

  it('renames a task inline', async () => {
    renderToday();
    await screen.findByText('Pay the internet bill');
    await userEvent.click(screen.getByRole('button', { name: 'Rename' }));

    const field = screen.getByLabelText('Rename');
    await userEvent.clear(field);
    await userEvent.type(field, 'Pay the internet');
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() =>
      expect(patchMock).toHaveBeenCalledWith('/tasks/t-1', { title: 'Pay the internet' }),
    );
    expect(await screen.findByText('Pay the internet')).toBeInTheDocument();
  });

  it('checks in a habit from the dashboard', async () => {
    renderToday();
    await screen.findByText('Morning workout');
    await userEvent.click(screen.getByRole('button', { name: 'Check in' }));

    await waitFor(() => expect(postMock).toHaveBeenCalledWith('/habits/h-1/log', { value: 1 }));
    expect(await screen.findByText('Habit logged for today.')).toBeInTheDocument();
  });

  it('restores a completed task when the request fails', async () => {
    postMock.mockRejectedValue(new Error('network down'));

    renderToday();
    await screen.findByText('Pay the internet bill');
    await userEvent.click(screen.getByRole('button', { name: 'Done' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'That change was not saved and has been reverted.',
    );
    await waitFor(() => expect(screen.getByText('Pay the internet bill')).toBeInTheDocument());
  });

  it('warns when the monthly budget is nearly spent', async () => {
    getMock.mockImplementation((path: string) =>
      Promise.resolve(
        String(path).startsWith('/habits') ? habitPage() : dashboard({ budget_warning: true }),
      ),
    );

    renderToday();

    expect(
      await screen.findByText('You are close to your monthly budget'),
    ).toBeInTheDocument();
  });

  it('shows empty states for a day without plans', async () => {
    getMock.mockImplementation((path: string) =>
      Promise.resolve(
        String(path).startsWith('/habits')
          ? { items: [], limit: 50, offset: 0, has_more: false }
          : dashboard({ task_items: [], events: [] }),
      ),
    );

    renderToday();

    const empty = await screen.findAllByText('Nothing planned yet. Capture something below.');
    expect(empty).toHaveLength(2);
    expect(screen.getByText('No active habits.')).toBeInTheDocument();
  });

  it('offers a retry after a failed dashboard request', async () => {
    getMock.mockRejectedValueOnce(new Error('network down'));
    getMock.mockImplementation((path: string) => Promise.resolve(route(path)));

    renderToday();

    expect(await screen.findByText('Could not load your dashboard.')).toBeInTheDocument();
  });

  it('shifts a due date by one day and keeps the time', () => {
    expect(nextDay('2026-09-18T15:00:00Z')).toBe('2026-09-19T15:00:00.000Z');
    expect(nextDay('2026-12-31T23:30:00Z')).toBe('2027-01-01T23:30:00.000Z');
  });

  it('ships every dashboard label in every locale', () => {
    const keys = Object.keys(TODAY_MESSAGES.en).sort();
    for (const locale of ['en', 'ru', 'pl', 'uk'] as const) {
      expect(Object.keys(TODAY_MESSAGES[locale]).sort()).toEqual(keys);
      for (const key of keys) expect(todayLabel(locale, key)).not.toBe(key);
    }
  });
});
