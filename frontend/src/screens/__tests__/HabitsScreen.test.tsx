import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import type { Mock } from 'vitest';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { HABIT_MESSAGES, habitLabel } from '@/i18n/habits';
import { api } from '@/lib/api';
import {
  type HabitPage,
  type HabitProgress,
  type HabitRecord,
  checkInValue,
  toggleDay,
} from '@/lib/habits';
import { HabitsScreen } from '@/screens/HabitsScreen';

vi.mock('@/lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn(), upload: vi.fn() },
  ApiError: class ApiError extends Error {},
}));

const getMock = api.get as unknown as Mock;
const postMock = api.post as unknown as Mock;
const patchMock = api.patch as unknown as Mock;
const delMock = api.del as unknown as Mock;

function habit(overrides: Partial<HabitRecord> = {}): HabitRecord {
  return {
    id: 'h-1',
    name: 'Morning workout',
    measurement_type: 'boolean',
    target_value: null,
    unit: null,
    active: true,
    reminder_hour: 7,
    source_inbox_item_id: null,
    created_at: '2026-09-17T10:00:00Z',
    ...overrides,
  };
}

function page(items: HabitRecord[] = [habit()]): HabitPage {
  return { items, limit: 50, offset: 0, has_more: false };
}

function progress(overrides: Partial<HabitProgress> = {}): HabitProgress {
  return {
    habit_id: 'h-1',
    name: 'Morning workout',
    period_start: '2026-08-19',
    period_end: '2026-09-18',
    scheduled_days: [1, 3, 5],
    expected: 13,
    completed: 9,
    missed: 4,
    percent: 69,
    ...overrides,
  };
}

function renderHabits(): HTMLElement {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const { container } = render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <HabitsScreen />
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
  getMock.mockImplementation((path: string) =>
    Promise.resolve(String(path).includes('/progress') ? progress() : page()),
  );
  postMock.mockResolvedValue(habit({ id: 'h-2' }));
  patchMock.mockResolvedValue(habit());
  delMock.mockResolvedValue(undefined);
});

describe('HabitsScreen', () => {
  it('lists active habits by default', async () => {
    renderHabits();

    expect(await screen.findByText('Morning workout')).toBeInTheDocument();
    expect(getMock.mock.calls[0]?.[0]).toBe('/habits?limit=50');
  });

  it('includes disabled habits on request', async () => {
    renderHabits();
    await screen.findByText('Morning workout');

    await userEvent.click(screen.getByLabelText('Show disabled habits'));

    await waitFor(() =>
      expect(getMock).toHaveBeenCalledWith('/habits?limit=50&include_inactive=true'),
    );
  });

  it('shows an empty state without habits', async () => {
    getMock.mockImplementation((path: string) =>
      Promise.resolve(String(path).includes('/progress') ? progress() : page([])),
    );

    renderHabits();

    expect(await screen.findByText('No habits yet.')).toBeInTheDocument();
  });

  it('creates a habit with an ISO weekday schedule', async () => {
    postMock.mockReturnValue(new Promise(() => undefined));

    renderHabits();
    await screen.findByText('Morning workout');
    await userEvent.type(screen.getByLabelText('Habit name'), 'Read 20 pages');
    await userEvent.selectOptions(screen.getByLabelText('Measurement'), 'numeric');
    await userEvent.type(screen.getByLabelText('Target'), '20');
    await userEvent.type(screen.getByLabelText('Unit'), 'pages');
    await userEvent.type(screen.getByLabelText('Reminder hour'), '21');
    await userEvent.click(screen.getByLabelText('Mon'));
    await userEvent.click(screen.getByLabelText('Wed'));
    await userEvent.click(screen.getByRole('button', { name: 'Add habit' }));

    expect(await screen.findByText('Read 20 pages')).toBeInTheDocument();
    expect(postMock).toHaveBeenCalledWith('/habits', {
      name: 'Read 20 pages',
      measurement_type: 'numeric',
      target_value: 20,
      unit: 'pages',
      schedule_days: [1, 3],
      reminder_hour: 21,
    });
  });

  it('keeps the add button disabled without a name', async () => {
    renderHabits();
    await screen.findByText('Morning workout');

    expect(screen.getByRole('button', { name: 'Add habit' })).toBeDisabled();
  });

  it('logs a check-in for a boolean habit', async () => {
    renderHabits();
    await screen.findByText('Morning workout');
    await userEvent.click(screen.getByRole('button', { name: 'Check in' }));

    await waitFor(() => expect(postMock).toHaveBeenCalledWith('/habits/h-1/log', { value: 1 }));
    expect(await screen.findByRole('status')).toHaveTextContent('Logged for today.');
  });

  it('logs the target value for a counted habit', async () => {
    getMock.mockImplementation((path: string) =>
      Promise.resolve(
        String(path).includes('/progress')
          ? progress()
          : page([habit({ measurement_type: 'numeric', target_value: 20, unit: 'pages' })]),
      ),
    );

    renderHabits();
    await screen.findByText('Morning workout');
    await userEvent.click(screen.getByRole('button', { name: 'Check in' }));

    await waitFor(() => expect(postMock).toHaveBeenCalledWith('/habits/h-1/log', { value: 20 }));
  });

  it('loads the progress of one habit on demand', async () => {
    renderHabits();
    await screen.findByText('Morning workout');
    await userEvent.click(screen.getByRole('button', { name: 'Progress' }));

    await waitFor(() =>
      expect(getMock).toHaveBeenCalledWith('/habits/h-1/progress?days=30'),
    );
    expect(await screen.findByText(/69%/)).toBeInTheDocument();
  });

  it('explains a period without scheduled days', async () => {
    getMock.mockImplementation((path: string) =>
      Promise.resolve(
        String(path).includes('/progress')
          ? progress({ percent: null, expected: 0, completed: 0, missed: 0 })
          : page(),
      ),
    );

    renderHabits();
    await screen.findByText('Morning workout');
    await userEvent.click(screen.getByRole('button', { name: 'Progress' }));

    expect(
      await screen.findByText('No scheduled days in this period.'),
    ).toBeInTheDocument();
  });

  it('renames a habit inline', async () => {
    renderHabits();
    await screen.findByText('Morning workout');
    await userEvent.click(screen.getByRole('button', { name: 'Rename' }));

    const field = screen.getByLabelText('Rename');
    await userEvent.clear(field);
    await userEvent.type(field, 'Evening workout');
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() =>
      expect(patchMock).toHaveBeenCalledWith('/habits/h-1', { name: 'Evening workout' }),
    );
  });

  it('disables a habit without deleting its history', async () => {
    postMock.mockReturnValue(new Promise(() => undefined));

    renderHabits();
    await screen.findByText('Morning workout');
    await userEvent.click(screen.getByRole('button', { name: 'Disable' }));

    expect(postMock).toHaveBeenCalledWith('/habits/h-1/disable');
    await waitFor(() => expect(screen.getByText(/disabled/)).toBeInTheDocument());
  });

  it('deletes a habit optimistically', async () => {
    delMock.mockReturnValue(new Promise(() => undefined));

    renderHabits();
    await screen.findByText('Morning workout');
    await userEvent.click(screen.getByRole('button', { name: 'Delete' }));

    await waitFor(() => expect(screen.queryByText('Morning workout')).toBeNull());
    expect(delMock).toHaveBeenCalledWith('/habits/h-1');
  });

  it('restores a deleted habit when the request fails', async () => {
    delMock.mockRejectedValue(new Error('network down'));

    renderHabits();
    await screen.findByText('Morning workout');
    await userEvent.click(screen.getByRole('button', { name: 'Delete' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'That change was not saved and has been reverted.',
    );
    await waitFor(() => expect(screen.getByText('Morning workout')).toBeInTheDocument());
  });

  it('offers a retry when habits cannot be loaded', async () => {
    getMock.mockRejectedValueOnce(new Error('network down'));
    getMock.mockImplementation((path: string) =>
      Promise.resolve(String(path).includes('/progress') ? progress() : page()),
    );

    renderHabits();

    expect(await screen.findByText('Could not load habits.')).toBeInTheDocument();
  });

  it('keeps the weekday selection sorted and reversible', () => {
    expect(toggleDay([], 3)).toEqual([3]);
    expect(toggleDay([3], 1)).toEqual([1, 3]);
    expect(toggleDay([1, 3], 3)).toEqual([1]);
  });

  it('derives the check-in value from the measurement type', () => {
    expect(checkInValue(habit())).toBe(1);
    expect(checkInValue(habit({ measurement_type: 'numeric', target_value: 20 }))).toBe(20);
    expect(checkInValue(habit({ measurement_type: 'numeric', target_value: null }))).toBe(1);
  });

  it('ships every habit label in every locale', () => {
    const keys = Object.keys(HABIT_MESSAGES.en).sort();
    for (const locale of ['en', 'ru', 'pl', 'uk'] as const) {
      expect(Object.keys(HABIT_MESSAGES[locale]).sort()).toEqual(keys);
      for (const key of keys) expect(habitLabel(locale, key)).not.toBe(key);
    }
  });
});
