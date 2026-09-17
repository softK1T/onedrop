import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { Mock } from 'vitest';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { api } from '@/lib/api';
import { AnalyticsScreen } from '@/screens/AnalyticsScreen';

vi.mock('@/lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn(), upload: vi.fn() },
  ApiError: class ApiError extends Error {},
}));

const getMock = api.get as unknown as Mock;

const EXPENSES = {
  summary: {
    total_minor: 45000,
    base_currency: 'PLN',
    categories: [{ category: 'transport', total_minor: 4500 }],
  },
  daily: [
    { day: '2026-09-16', value: 0 },
    { day: '2026-09-17', value: 4500 },
  ],
};

const PRODUCTIVITY = {
  completion_percent: 72,
  captures_total: 18,
  captures_failed: 1,
  captures_undone: 2,
};

function route(path: string): unknown {
  return path.startsWith('/analytics/expenses') ? EXPENSES : PRODUCTIVITY;
}

function renderAnalytics(): HTMLElement {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const { container } = render(
    <QueryClientProvider client={client}>
      <AnalyticsScreen />
    </QueryClientProvider>,
  );
  return container;
}

beforeEach(() => {
  getMock.mockReset();
});

describe('AnalyticsScreen', () => {
  it('shows skeletons while both queries load', () => {
    getMock.mockReturnValue(new Promise(() => undefined));

    const container = renderAnalytics();

    expect(container.querySelectorAll('.od-skeleton').length).toBeGreaterThan(0);
  });

  it('renders expenses, productivity and capture totals', async () => {
    getMock.mockImplementation((path: string) => Promise.resolve(route(path)));

    const container = renderAnalytics();

    expect(await screen.findByRole('heading', { name: 'Analytics' })).toBeInTheDocument();
    expect(container.textContent).toContain('450');
    expect(container.textContent).toContain('PLN');
    expect(container.textContent).toContain('72%');
    expect(container.textContent).toContain('18');
  });

  it('shows an empty state when nothing was spent in the period', async () => {
    getMock.mockImplementation((path: string) =>
      Promise.resolve(
        path.startsWith('/analytics/expenses')
          ? { ...EXPENSES, daily: [{ day: '2026-09-16', value: 0 }] }
          : PRODUCTIVITY,
      ),
    );

    renderAnalytics();

    expect(await screen.findByText('Not enough data yet.')).toBeInTheDocument();
  });

  it('retries both queries after a failure', async () => {
    getMock.mockRejectedValueOnce(new Error('network down'));
    getMock.mockRejectedValueOnce(new Error('network down'));
    getMock.mockImplementation((path: string) => Promise.resolve(route(path)));

    renderAnalytics();

    expect(await screen.findByText('Could not load analytics.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByRole('heading', { name: 'Analytics' })).toBeInTheDocument();
  });
});
