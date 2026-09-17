import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import type { Mock } from 'vitest';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { Dashboard } from '@/app/types';
import { api } from '@/lib/api';
import { TodayScreen } from '@/screens/TodayScreen';

vi.mock('@/lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn(), upload: vi.fn() },
  ApiError: class ApiError extends Error {},
}));

const getMock = api.get as unknown as Mock;

function dashboard(overrides: Partial<Dashboard> = {}): Dashboard {
  return {
    day: '2026-09-18',
    timezone: 'Europe/Warsaw',
    tasks: { today: 2, overdue: 1, completed_today: 3, open_total: 5 },
    task_items: [
      { id: 't-1', title: 'Pay the internet bill', due_at: null, priority: 'high', status: 'open' },
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
});

describe('TodayScreen', () => {
  it('renders a busy skeleton while the dashboard loads', () => {
    getMock.mockReturnValue(new Promise(() => undefined));

    const container = renderToday();

    expect(container.querySelector('[aria-busy="true"]')).not.toBeNull();
  });

  it('shows the dashboard metrics, tasks and events', async () => {
    getMock.mockResolvedValue(dashboard());

    renderToday();

    expect(await screen.findByRole('heading', { level: 1, name: 'Today' })).toBeInTheDocument();
    expect(screen.getByText('Pay the internet bill')).toBeInTheDocument();
    expect(screen.getByText('Meeting with Andrew')).toBeInTheDocument();
    expect(screen.getByText('AI actions left')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
    expect(screen.getByText('1850')).toBeInTheDocument();
    expect(screen.getByText(/45/)).toBeInTheDocument();
  });

  it('requests the dashboard endpoint exactly once', async () => {
    getMock.mockResolvedValue(dashboard());

    renderToday();
    await screen.findByText('Pay the internet bill');

    expect(getMock).toHaveBeenCalledTimes(1);
    expect(getMock.mock.calls[0]?.[0]).toBe('/dashboard/today');
  });

  it('shows an empty state for a day without tasks or events', async () => {
    getMock.mockResolvedValue(dashboard({ task_items: [], events: [] }));

    renderToday();

    const empty = await screen.findAllByText('Nothing planned yet. Capture something below.');
    expect(empty).toHaveLength(2);
  });

  it('warns when the monthly budget is nearly spent', async () => {
    getMock.mockResolvedValue(dashboard({ budget_warning: true }));

    renderToday();

    expect(
      await screen.findByText('You are close to your monthly budget'),
    ).toBeInTheDocument();
  });

  it('hides the budget warning by default', async () => {
    getMock.mockResolvedValue(dashboard());

    renderToday();
    await screen.findByText('Pay the internet bill');

    expect(screen.queryByText('You are close to your monthly budget')).toBeNull();
  });

  it('offers a retry after a failed request and recovers', async () => {
    getMock.mockRejectedValueOnce(new Error('network down'));
    getMock.mockResolvedValueOnce(dashboard());

    renderToday();

    expect(await screen.findByText('Could not load your dashboard.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByText('Pay the internet bill')).toBeInTheDocument();
    expect(getMock).toHaveBeenCalledTimes(2);
  });
});
