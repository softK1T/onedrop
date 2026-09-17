import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { Mock } from 'vitest';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { UserProfile, UserSettings } from '@/app/types';
import { SETTINGS_MESSAGES, settingsLabel } from '@/i18n/settings';
import { api } from '@/lib/api';
import { SettingsScreen } from '@/screens/SettingsScreen';

vi.mock('@/lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn(), upload: vi.fn() },
  ApiError: class ApiError extends Error {},
}));

const getMock = api.get as unknown as Mock;
const patchMock = api.patch as unknown as Mock;

function settings(overrides: Partial<UserSettings> = {}): UserSettings {
  return {
    timezone: 'Europe/Warsaw',
    base_currency: 'PLN',
    monthly_budget_minor: 300000,
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
    ...overrides,
  };
}

function profile(overrides: Partial<UserProfile> = {}): UserProfile {
  return {
    first_name: 'Nazar',
    username: 'softkit',
    locale: 'en',
    settings: settings(),
    ...overrides,
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

  it('prefills general and reminder preferences', async () => {
    getMock.mockResolvedValue(profile());

    renderSettings();

    expect(await screen.findByLabelText('Timezone')).toHaveValue('Europe/Warsaw');
    expect(screen.getByLabelText('Currency')).toHaveValue('PLN');
    expect(screen.getByLabelText('Monthly budget')).toHaveValue(3000);
    expect(screen.getByLabelText('Digest hour')).toHaveValue(8);
    expect(screen.getByLabelText('Task lead time, minutes')).toHaveValue(30);
    expect(screen.getByLabelText('Event lead time, minutes')).toHaveValue(60);
    expect(screen.getByLabelText('Quiet from')).toHaveValue(22);
    expect(screen.getByLabelText('Quiet until')).toHaveValue(7);
    expect(screen.getByLabelText('Warn at percent of budget')).toHaveValue(80);
  });

  it('saves the timezone when the field loses focus', async () => {
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

  it('saves quiet hours, lead times and the budget threshold', async () => {
    getMock.mockResolvedValue(profile());

    renderSettings();
    const quietFrom = await screen.findByLabelText('Quiet from');
    await userEvent.clear(quietFrom);
    await userEvent.type(quietFrom, '23');
    await userEvent.tab();
    await waitFor(() =>
      expect(patchMock).toHaveBeenCalledWith('/me/settings', { quiet_hours_start: 23 }),
    );

    const lead = screen.getByLabelText('Task lead time, minutes');
    await userEvent.clear(lead);
    await userEvent.type(lead, '45');
    await userEvent.tab();
    await waitFor(() =>
      expect(patchMock).toHaveBeenCalledWith('/me/settings', {
        task_reminder_lead_minutes: 45,
      }),
    );

    const threshold = screen.getByLabelText('Warn at percent of budget');
    await userEvent.clear(threshold);
    await userEvent.type(threshold, '90');
    await userEvent.tab();
    await waitFor(() =>
      expect(patchMock).toHaveBeenCalledWith('/me/settings', {
        budget_warning_threshold_percent: 90,
      }),
    );
  });

  it('ignores an out-of-range value instead of sending it', async () => {
    getMock.mockResolvedValue(profile());

    renderSettings();
    const threshold = await screen.findByLabelText('Warn at percent of budget');
    await userEvent.clear(threshold);
    await userEvent.type(threshold, '150');
    await userEvent.tab();

    expect(patchMock).not.toHaveBeenCalled();
  });

  it('applies a toggle optimistically before the server answers', async () => {
    getMock.mockResolvedValue(profile());
    patchMock.mockReturnValue(new Promise(() => undefined));

    renderSettings();
    const digest = await screen.findByLabelText('Morning digest');
    await userEvent.click(digest);

    expect(digest).not.toBeChecked();
    expect(patchMock).toHaveBeenCalledWith('/me/settings', { morning_digest: false });
  });

  it('rolls the toggle back and explains a failed save', async () => {
    getMock.mockResolvedValue(profile());
    patchMock.mockRejectedValue(new Error('network down'));

    renderSettings();
    await userEvent.click(await screen.findByLabelText('Habit reminders'));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not save that change. It was reverted.',
    );
    await waitFor(() => expect(screen.getByLabelText('Habit reminders')).toBeChecked());
  });

  it('disables the per-kind switches when reminders are off', async () => {
    getMock.mockResolvedValue(profile({ settings: settings({ reminders_enabled: false }) }));

    renderSettings();

    expect(await screen.findByLabelText('Morning digest')).toBeDisabled();
    expect(screen.getByLabelText('Task reminders')).toBeDisabled();
    expect(screen.getByLabelText('Quiet from')).toBeDisabled();
    expect(screen.getByLabelText('Reminders')).toBeEnabled();
  });

  it('renders labels in the profile locale', async () => {
    getMock.mockResolvedValue(profile({ locale: 'uk' }));

    renderSettings();

    expect(await screen.findByLabelText('Часовий пояс')).toHaveValue('Europe/Warsaw');
    expect(screen.getByRole('heading', { name: 'Налаштування' })).toBeInTheDocument();
  });

  it('offers a retry when settings cannot be loaded', async () => {
    getMock.mockRejectedValueOnce(new Error('network down'));
    getMock.mockResolvedValueOnce(profile());

    renderSettings();

    expect(await screen.findByText('Could not load settings.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByLabelText('Timezone')).toHaveValue('Europe/Warsaw');
  });

  it('ships every settings label in every locale', () => {
    const keys = Object.keys(SETTINGS_MESSAGES.en).sort();
    for (const locale of ['en', 'ru', 'pl', 'uk'] as const) {
      expect(Object.keys(SETTINGS_MESSAGES[locale]).sort()).toEqual(keys);
      for (const key of keys) expect(settingsLabel(locale, key)).not.toBe(key);
    }
  });
});
