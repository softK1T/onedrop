import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { Mock } from 'vitest';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { api } from '@/lib/api';
import { SubscriptionScreen } from '@/screens/SubscriptionScreen';

vi.mock('@/lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn(), upload: vi.fn() },
  ApiError: class ApiError extends Error {},
}));

const getMock = api.get as unknown as Mock;
const postMock = api.post as unknown as Mock;
const assign = vi.fn();

interface PlanResponse {
  plan: string;
  status: string;
  expires_at: string | null;
  pro_price_stars: number;
  pro_period_days: number;
  features: {
    photo_recognition: boolean;
    morning_digest: boolean;
    advanced_analytics: boolean;
    csv_export: boolean;
  };
}

function plan(overrides: Partial<PlanResponse> = {}): PlanResponse {
  return {
    plan: 'free',
    status: 'active',
    expires_at: null,
    pro_price_stars: 250,
    pro_period_days: 30,
    features: {
      photo_recognition: true,
      morning_digest: true,
      advanced_analytics: true,
      csv_export: true,
    },
    ...overrides,
  };
}

function renderSubscription(): HTMLElement {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const { container } = render(
    <QueryClientProvider client={client}>
      <SubscriptionScreen />
    </QueryClientProvider>,
  );
  return container;
}

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
  assign.mockReset();
  Object.defineProperty(window, 'location', {
    writable: true,
    value: { assign, href: 'http://localhost/' },
  });
});

describe('SubscriptionScreen', () => {
  it('shows a skeleton while the plan loads', () => {
    getMock.mockReturnValue(new Promise(() => undefined));

    const container = renderSubscription();

    expect(container.querySelectorAll('.od-skeleton').length).toBeGreaterThan(0);
  });

  it('offers the paywall with the configured Stars price on the free plan', async () => {
    getMock.mockResolvedValue(plan());

    const container = renderSubscription();

    expect(await screen.findByText('Free plan')).toBeInTheDocument();
    expect(container.textContent).toContain('250 Stars');
    expect(container.textContent).toContain('30 days');
  });

  it('creates a Stars invoice and follows the returned link', async () => {
    getMock.mockResolvedValue(plan());
    postMock.mockResolvedValue({
      invoice_link: 'https://t.me/invoice/abc',
      amount_stars: 250,
      currency: 'XTR',
      period_days: 30,
    });

    renderSubscription();
    await userEvent.click(await screen.findByRole('button', { name: /Get Pro/ }));

    await waitFor(() =>
      expect(postMock).toHaveBeenCalledWith('/billing/invoice', { plan: 'pro' }),
    );
    await waitFor(() => expect(assign).toHaveBeenCalledWith('https://t.me/invoice/abc'));
  });

  it('hides the paywall for an active Pro subscription', async () => {
    getMock.mockResolvedValue(
      plan({ plan: 'pro', expires_at: '2026-10-18T00:00:00Z' }),
    );

    renderSubscription();

    expect(await screen.findByText('Pro plan')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Get Pro/ })).toBeNull();
  });

  it('reports a failed invoice without pretending the plan changed', async () => {
    getMock.mockResolvedValue(plan());
    postMock.mockRejectedValue(new Error('billing unavailable'));

    renderSubscription();
    await userEvent.click(await screen.findByRole('button', { name: /Get Pro/ }));

    expect(
      await screen.findByText('Could not create invoice. Open the bot and try again.'),
    ).toBeInTheDocument();
    expect(assign).not.toHaveBeenCalled();
  });

  it('offers a retry when the plan request fails', async () => {
    getMock.mockRejectedValueOnce(new Error('network down'));
    getMock.mockResolvedValueOnce(plan());

    renderSubscription();

    expect(await screen.findByText('Could not load subscription.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByText('Free plan')).toBeInTheDocument();
  });
});
