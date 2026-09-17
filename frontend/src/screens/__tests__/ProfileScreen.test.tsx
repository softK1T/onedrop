import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import type { Mock } from 'vitest';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { UserProfile } from '@/app/types';
import { api } from '@/lib/api';
import { ProfileScreen } from '@/screens/ProfileScreen';

vi.mock('@/lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn(), upload: vi.fn() },
  ApiError: class ApiError extends Error {},
}));

const getMock = api.get as unknown as Mock;

function profile(overrides: Partial<UserProfile> = {}): UserProfile {
  return {
    first_name: 'Nazar',
    username: 'softkit',
    locale: 'en',
    settings: {
      timezone: 'Europe/Warsaw',
      base_currency: 'PLN',
      monthly_budget_minor: null,
      reminders_enabled: true,
      task_reminders: true,
      event_reminders: true,
      habit_reminders: true,
      morning_digest: true,
      budget_warnings: true,
      morning_digest_hour: 8,
      quiet_hours_start: 22,
      quiet_hours_end: 7,
      task_reminder_lead_minutes: 30,
      event_reminder_lead_minutes: 60,
      budget_warning_threshold_percent: 80,
      allow_training: false,
    },
    ...overrides,
  };
}

function renderProfile(): void {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ProfileScreen />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  getMock.mockReset();
});

describe('ProfileScreen', () => {
  it('shows the Telegram name and handle', async () => {
    getMock.mockResolvedValue(profile());

    renderProfile();

    expect(await screen.findByText('Nazar')).toBeInTheDocument();
    expect(screen.getByText('@softkit')).toBeInTheDocument();
  });

  it('falls back to a neutral name and the timezone', async () => {
    getMock.mockResolvedValue(profile({ first_name: null, username: null }));

    renderProfile();

    expect(await screen.findByText('OneDrop user')).toBeInTheDocument();
    expect(screen.getByText('Europe/Warsaw')).toBeInTheDocument();
  });

  it('links to settings, subscription and privacy', async () => {
    getMock.mockResolvedValue(profile());

    renderProfile();
    await screen.findByText('Nazar');

    expect(screen.getByRole('link', { name: /Settings/ })).toHaveAttribute('href', '/settings');
    expect(screen.getByRole('link', { name: /Subscription/ })).toHaveAttribute(
      'href',
      '/subscription',
    );
    expect(screen.getByRole('link', { name: /Privacy/ })).toHaveAttribute('href', '/privacy');
  });

  it('offers a retry when the profile cannot be loaded', async () => {
    getMock.mockRejectedValueOnce(new Error('network down'));
    getMock.mockResolvedValueOnce(profile());

    renderProfile();

    expect(await screen.findByText('Could not load profile.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByText('Nazar')).toBeInTheDocument();
  });
});
