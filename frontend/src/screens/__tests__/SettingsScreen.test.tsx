import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { Mock } from 'vitest';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { UserProfile } from '@/app/types';
import { api } from '@/lib/api';
import { SettingsScreen } from '@/screens/SettingsScreen';

vi.mock('@/lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn(), upload: vi.fn() },
  ApiError: class ApiError extends Error {},
}));

const getMock = api.get as unknown as Mock;
const patchMock = api.patch as unknown as Mock;

function profile(overrides: Partial<UserProfile['settings']> = {}): UserProfile {
  return {
    first_name: 'Nazar',
    username: 'softkit',
    locale: 'en',
    settings: {
      timezone: 'Europe/Warsaw',
      base_currency: 'PLN',
      monthly_budget_minor: 300000,
      reminders_enabled: true,
      allow_training: false,
      ...overrides,
    },
  };
}

function renderSettings(): HTMLElement {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const { container } = render(
    <QueryClientProvider client={client}>
      <SettingsScreen />
    </QueryClientProvider>,
  );
  return container;
}

beforeEach(() => {
  getMock.mockReset();
  patchMock.mockReset();
  patchMock.mockResolvedValue({});
});

describe('SettingsScreen', () => {
  it('shows a skeleton while the profile loads', () => {
    getMock.mockReturnValue(new Promise(() => undefined));

    const container = renderSettings();

    expect(container.querySelectorAll('.od-skeleton').length).toBeGreaterThan(0);
  });

  it('prefills the stored timezone, currency and reminder switch', async () => {
    getMock.mockResolvedValue(profile());

    renderSettings();

    expect(await screen.findByLabelText('Timezone')).toHaveValue('Europe/Warsaw');
    expect(screen.getByLabelText('Currency')).toHaveValue('PLN');
    expect(screen.getByLabelText('Reminders')).toBeChecked();
  });

  it('saves a new timezone when the field loses focus', async () => {
    getMock.mockResolvedValue(profile());

    renderSettings();
    const field = await screen.findByLabelText('Timezone');
    await userEvent.clear(field);
    await userEvent.type(field, 'Europe/Kyiv');
    await userEvent.tab();

    await waitFor(() =>
      expect(patchMock).toHaveBeenCalledWith('/me/settings', { timezone: 'Europe/Kyiv' }),
    );
  });

  it('saves the base currency immediately', async () => {
    getMock.mockResolvedValue(profile());

    renderSettings();
    await userEvent.selectOptions(await screen.findByLabelText('Currency'), 'EUR');

    await waitFor(() =>
      expect(patchMock).toHaveBeenCalledWith('/me/settings', { base_currency: 'EUR' }),
    );
  });

  it('turns reminders off through the switch', async () => {
    getMock.mockResolvedValue(profile());

    renderSettings();
    await userEvent.click(await screen.findByLabelText('Reminders'));

    await waitFor(() =>
      expect(patchMock).toHaveBeenCalledWith('/me/settings', { reminders_enabled: false }),
    );
  });

  it('offers a retry when settings cannot be loaded', async () => {
    getMock.mockRejectedValueOnce(new Error('network down'));
    getMock.mockResolvedValueOnce(profile());

    renderSettings();

    expect(await screen.findByText('Could not load settings.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByLabelText('Timezone')).toHaveValue('Europe/Warsaw');
  });
});
